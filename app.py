from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import pandas as pd
from datetime import datetime
import plotly
import plotly.graph_objs as go
import json
from model import load_model, predict_form
from models import db, User, ExerciseEntry  # Import our database models

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-goes-here'  # Change this to a random secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exercise_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GOLDEN_DATA_FOLDER'] = 'golden_data'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

# Initialize the database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure upload and golden data folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['GOLDEN_DATA_FOLDER']):
    os.makedirs(app.config['GOLDEN_DATA_FOLDER'])

# Define our 5 exercise types
EXERCISE_TYPES = ['Lateral raises', 'Single arm extensions', 'Bicep curls', 'Hammer curls', 'Single arm tricep extensions']

# Helper function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Create a function to get user-specific upload folder
def get_user_upload_folder(user_id):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
            
        login_user(user, remember=True)
        return redirect(url_for('index'))
        
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Group exercise entries by type
    exercise_groups = {}
    for ex_type in EXERCISE_TYPES:
        entries = ExerciseEntry.query.filter_by(
            user_id=current_user.id, 
            exercise_type=ex_type
        ).all()
        
        exercise_groups[ex_type] = {
            'name': ex_type,
            'entries': entries,
            'has_data': len(entries) > 0
        }
    
    return render_template('index.html', exercise_groups=exercise_groups)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Get form data
        exercise_type = request.form['exercise_type']
        exercise_date = request.form['exercise_date']
        file = request.files['file']

        if file and allowed_file(file.filename):
            # Format the date for display and filenames
            display_date = datetime.strptime(exercise_date, '%Y-%m-%d').strftime('%B %d, %Y')
            date_code = exercise_date.replace('-', '')
            
            # Get user-specific upload folder
            user_folder = get_user_upload_folder(current_user.id)
            
            # Save the file
            filename = f"{exercise_type}_{date_code}.csv"
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)

            # Load the corresponding trained model
            try:
                model = load_model(exercise_type)
            except FileNotFoundError:
                flash(f"No trained model found for exercise: {exercise_type}")
                return redirect(url_for('upload'))

            # Load the user's CSV file
            user_df = pd.read_csv(filepath)

            # Predict form correctness using the trained model
            predictions = predict_form(model, user_df)

            # Calculate accuracy
            total_count = len(predictions)
            correct_count = sum(predictions)  # Assuming 1 = proper form, 0 = improper form
            accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

            # Add exercise data to the database
            new_entry = ExerciseEntry(
                exercise_type=exercise_type,
                display_date=display_date,
                date_code=date_code,
                filename=filename,
                accuracy=round(accuracy, 1),
                date=exercise_date,
                user_id=current_user.id
            )
            db.session.add(new_entry)
            db.session.commit()

            flash('Data uploaded successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid file format. Please upload a CSV file.')
            
    return render_template('upload.html')

@app.route('/dashboard/<exercise_type>')
@login_required
def dashboard(exercise_type):
    # Get all entries for this exercise type and current user
    entries = ExerciseEntry.query.filter_by(
        user_id=current_user.id,
        exercise_type=exercise_type
    ).order_by(ExerciseEntry.date).all()
    
    if not entries:
        flash('No data found for this exercise')
        return redirect(url_for('index'))

    # Create plots for each date
    plots = []
    
    # Collect data for progress chart
    progress_dates = []
    progress_accuracies = []
    
    for entry in entries:
        # Get user-specific upload folder
        user_folder = get_user_upload_folder(current_user.id)
        
        # Load the user CSV data
        filepath = os.path.join(user_folder, entry.filename)
        if not os.path.exists(filepath):
            continue

        # Add data for progress chart
        progress_dates.append(entry.display_date)
        progress_accuracies.append(entry.accuracy)

        # Load the corresponding trained model
        try:
            model = load_model(exercise_type)
        except FileNotFoundError:
            continue

        # Load the user's CSV file
        user_df = pd.read_csv(filepath)

        # Predict form correctness using the trained model
        predictions = predict_form(model, user_df)

        # Calculate performance metrics
        total_count = len(predictions)
        correct_count = sum(predictions)  # Assuming 1 = proper form, 0 = improper form
        user_accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        # Load golden data for comparison
        golden_data_path = os.path.join(app.config['GOLDEN_DATA_FOLDER'], exercise_type, "golden_data.csv")
        if os.path.exists(golden_data_path):
            golden_df = pd.read_csv(golden_data_path)
        else:
            golden_df = pd.DataFrame()  # Empty DataFrame if golden data is not found

        # Create 3D plots for accelerometer and gyroscope data
        acc_3d_fig = go.Figure()
        gyro_3d_fig = go.Figure()

        # Add user accelerometer data to the 3D plot
        acc_3d_fig.add_trace(go.Scatter3d(
            x=user_df["lsm6dsv16x_acc_x [g]"],
            y=user_df["lsm6dsv16x_acc_y [g]"],
            z=user_df["lsm6dsv16x_acc_z [g]"],
            mode='lines',
            name='User Acc',
            line=dict(color='blue', width=2)
        ))

        # Add golden accelerometer data to the 3D plot
        if not golden_df.empty:
            acc_3d_fig.add_trace(go.Scatter3d(
                x=golden_df["lsm6dsv16x_acc_x [g]"],
                y=golden_df["lsm6dsv16x_acc_y [g]"],
                z=golden_df["lsm6dsv16x_acc_z [g]"],
                mode='lines',
                name='Golden Acc',
                line=dict(color='green', width=2, dash='dash')
            ))

        # Update layout for the accelerometer 3D plot
        acc_3d_fig.update_layout(
            title=f"Accelerometer Data: {entry.display_date}",
            scene=dict(
                xaxis_title='Acc X [g]',
                yaxis_title='Acc Y [g]',
                zaxis_title='Acc Z [g]'
            ),
            height=500,
            margin=dict(l=50, r=50, t=80, b=50)
        )

        # Add user gyroscope data to the 3D plot
        gyro_3d_fig.add_trace(go.Scatter3d(
            x=user_df["lsm6dsv16x_gyro_x [dps]"],
            y=user_df["lsm6dsv16x_gyro_y [dps]"],
            z=user_df["lsm6dsv16x_gyro_z [dps]"],
            mode='lines',
            name='User Gyro',
            line=dict(color='red', width=2)
        ))

        # Add golden gyroscope data to the 3D plot
        if not golden_df.empty:
            gyro_3d_fig.add_trace(go.Scatter3d(
                x=golden_df["lsm6dsv16x_gyro_x [dps]"],
                y=golden_df["lsm6dsv16x_gyro_y [dps]"],
                z=golden_df["lsm6dsv16x_gyro_z [dps]"],
                mode='lines',
                name='Golden Gyro',
                line=dict(color='orange', width=2, dash='dash')
            ))

        # Update layout for the gyroscope 3D plot
        gyro_3d_fig.update_layout(
            title=f"Gyroscope Data: {entry.display_date}",
            scene=dict(
                xaxis_title='Gyro X [dps]',
                yaxis_title='Gyro Y [dps]',
                zaxis_title='Gyro Z [dps]'
            ),
            height=500,
            margin=dict(l=50, r=50, t=80, b=50)
        )

        # Convert the figures to JSON
        acc_3d_graphJSON = json.dumps(acc_3d_fig, cls=plotly.utils.PlotlyJSONEncoder)
        gyro_3d_graphJSON = json.dumps(gyro_3d_fig, cls=plotly.utils.PlotlyJSONEncoder)

        # Add the 3D plots to the plots list
        plots.append({
            'acc_3d_graphJSON': acc_3d_graphJSON,
            'gyro_3d_graphJSON': gyro_3d_graphJSON,
            'date': entry.display_date,
            'accuracy': entry.accuracy
        })
    
        
    # Create progress chart if there's more than one data point
    progress_chart = None
    if len(progress_dates) > 1:
        # Calculate improvement between first and last sessions
        first_accuracy = progress_accuracies[0]
        last_accuracy = progress_accuracies[-1]
        improvement = last_accuracy - first_accuracy
        
        # Create progress chart
        progress_fig = go.Figure()
        progress_fig.add_trace(go.Scatter(
            x=progress_dates, 
            y=progress_accuracies,
            mode='lines+markers',
            name='Accuracy',
            line=dict(color='#007bff', width=3),
            marker=dict(size=10)
        ))
        
        # Add annotation for improvement
        if improvement != 0:
            annotation_text = f"{'+' if improvement > 0 else ''}{improvement:.1f}% change"
            progress_fig.add_annotation(
                x=progress_dates[-1],
                y=progress_accuracies[-1],
                text=annotation_text,
                showarrow=True,
                arrowhead=1,
                ax=0,
                ay=-40,
                font=dict(size=14, color='black'),
                bgcolor=('#28a745' if improvement > 0 else '#dc3545')
            )
        
        progress_fig.update_layout(
            title=f"{exercise_type.capitalize()} Performance Progress",
            xaxis_title="Date",
            yaxis_title="Accuracy (%)",
            yaxis=dict(range=[0, 105]),  # Set y-axis to start at 0 and go slightly above 100 for annotations
            height=400,
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_white"
        )
        
        progress_chart = json.dumps(progress_fig, cls=plotly.utils.PlotlyJSONEncoder)
        
    return render_template('dashboard.html', 
                          exercise_type=exercise_type,
                          plots=plots,
                          progress_chart=progress_chart)

if __name__ == '__main__':
    app.run(debug=True)