from flask import Flask, render_template, request, redirect, url_for
import os
import csv
from datetime import datetime
import plotly
import plotly.graph_objs as go
import json
import pandas as pd  # Add pandas for CSV handling

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Helper function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Define our 5 exercise types
EXERCISE_TYPES = ['Lateral raises', 'Single arm extensions', 'Bicep curls', 'Hammer curls', 'Single arm tricep extensions']

# Store for exercise data entries
exercise_entries = []

@app.route('/')
def index():
    # Group exercise entries by type
    exercise_groups = {}
    for ex_type in EXERCISE_TYPES:
        exercise_groups[ex_type] = {
            'name': ex_type,
            'entries': [entry for entry in exercise_entries if entry['exercise_type'] == ex_type],
            'has_data': any(entry['exercise_type'] == ex_type for entry in exercise_entries)
        }
    
    return render_template('index.html', exercise_groups=exercise_groups)

@app.route('/upload', methods=['GET', 'POST'])
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
            
            # Save the file
            filename = f"{exercise_type}_{date_code}.csv"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Parse CSV and extract data
            user_df = pd.read_csv(filepath)
            total_count = len(user_df)
            correct_count = user_df[user_df['label'] == 'correct_form'].shape[0]
            accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

            # Add exercise data to the list
            exercise_entries.append({
                'exercise_type': exercise_type,
                'display_date': display_date,
                'date_code': date_code,
                'filename': filename,
                'accuracy': round(accuracy, 1),
                'date': exercise_date  # Store the raw date for sorting
            })

            return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/dashboard/<exercise_type>')
def dashboard(exercise_type):
    """
    Dashboard for a single exercise type.
    Shows multiple plots for different dates if available.
    """
    # Get all entries for this exercise type
    entries = [entry for entry in exercise_entries if entry['exercise_type'] == exercise_type]
    
    if not entries:
        return "No data found for this exercise", 404

    # Create plots for each date
    plots = []
    
    # Collect data for progress chart
    progress_dates = []
    progress_accuracies = []
    
    # Sort entries by date for the progress chart
    sorted_entries = sorted(entries, key=lambda x: x.get('date', ''))
    
    for entry in sorted_entries:
        # Load the user CSV data
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], entry['filename'])
        if not os.path.exists(filepath):
            continue

        # Add data for progress chart
        progress_dates.append(entry['display_date'])
        progress_accuracies.append(entry['accuracy'])

        user_df = pd.read_csv(filepath)
        
        # Calculate performance metrics
        total_count = len(user_df)
        correct_count = user_df[user_df['label'] == 'correct_form'].shape[0]
        user_accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
        # For golden data we assume 100% correct (or you could compute other metrics)
        golden_accuracy = 100

        # Create a grouped bar chart comparing the user vs. golden performance
        fig = go.Figure(data=[
            go.Bar(name='User', x=['Performance'], y=[user_accuracy], marker_color='blue'),
            go.Bar(name='Golden Standard', x=['Performance'], y=[golden_accuracy], marker_color='green')
        ])
        fig.update_layout(
            barmode='group', 
            title=f"Exercise Form: {entry['display_date']}",
            yaxis=dict(title="Accuracy (%)"),
            height=400,
        )
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        plots.append({
            'graphJSON': graphJSON,
            'date': entry['display_date'],
            'accuracy': entry['accuracy']
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