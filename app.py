from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
import json
import plotly
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Folder for pre-programmed golden data CSVs
GOLDEN_DATA_DIR = 'golden_data'
os.makedirs(GOLDEN_DATA_DIR, exist_ok=True)

def load_golden_data(exercise_name):
    """
    Load the golden CSV data for a given exercise.
    This example expects a file named like exercise1.csv in the golden_data folder.
    """
    golden_file = os.path.join(GOLDEN_DATA_DIR, f"{exercise_name}.csv")
    if os.path.exists(golden_file):
        return pd.read_csv(golden_file)
    else:
        # Return an empty DataFrame if no golden data is found.
        return pd.DataFrame()

@app.route('/')
def index():
    """
    Home page: lists previously uploaded exercise CSVs.
    The filenames are expected to be of the format YYYY-MM-DD_exercise.csv.
    """
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    uploads = []
    for file in files:
        parts = file.split('_')
        if len(parts) >= 2:
            date_str = parts[0]
            exercise = parts[1].replace('.csv', '')
            uploads.append({'date': date_str, 'exercise': exercise, 'filename': file})
    return render_template('index.html', uploads=uploads)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    Page for uploading a new CSV file.
    The user selects an exercise (one of five) and uploads a CSV file.
    """
    if request.method == 'POST':
        file = request.files.get('file')
        exercise = request.form.get('exercise')
        if file and exercise:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"{date_str}_{exercise}.csv"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('dashboard', filename=filename))
    return render_template('upload.html')

@app.route('/dashboard/<filename>')
def dashboard(filename):
    """
    Dashboard for a single upload.
    Loads the user CSV file and compares the performance (percentage of correct_form readings)
    to the golden data (assumed to represent 100% correct form).
    A Plotly bar chart is rendered.
    """
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    # Load the user CSV data (assumed columns: time, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, label)
    user_df = pd.read_csv(filepath)
    # Extract exercise name from filename (format: YYYY-MM-DD_exercise.csv)
    exercise = filename.split('_')[1].replace('.csv', '')

    # Load the golden data (if available)
    golden_df = load_golden_data(exercise)
    
    # Calculate performance metrics
    total_count = len(user_df)
    correct_count = user_df[user_df['label'] == 'correct_form'].shape[0]
    user_accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    # For golden data we assume 100% correct (or you could compute other metrics)
    golden_accuracy = 100

    # Create a grouped bar chart comparing the user vs. golden performance
    fig = go.Figure(data=[
        go.Bar(name='User', x=[exercise], y=[user_accuracy]),
        go.Bar(name='Golden', x=[exercise], y=[golden_accuracy])
    ])
    fig.update_layout(barmode='group', title="Exercise Form Comparison",
                      yaxis=dict(title="Accuracy (%)"))
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('dashboard.html', graphJSON=graphJSON, 
                           exercise=exercise, user_accuracy=user_accuracy)

if __name__ == '__main__':
    app.run(debug=True)
