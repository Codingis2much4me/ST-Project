# GymMetrics - Exercise Dashboard
Repository for the ST Project Dashboard.

To help you get started with the software, we have created a step-by-step video guide that explains the main features and how to use them.

Watch the video below for a comprehensive walkthrough:
[Click Here](IITGoa_DemoVideo.mp4)

In the video, you'll learn how to:
- Record and Upload the data
- Navigate through the user interface
- Perform common tasks
- Familiarize yourself to the Gymmetrics Dashboard   

If you prefer written instructions, check out the rest of the documentation below!

## NOTE
Our team's detailed project report is present in [Project Report](ST_Project_IIT_Goa.pdf)

## NOTE
The datasets required for this project are stored in the training_data and golden_data folders. Please ensure these folders are properly populated with the necessary data before running the project.

## Description

The Exercise Tracking Dashboard is a web-based application built using Flask, Bootstrap, and Plotly. It allows users to upload CSV files containing exercise data, visualize accuracy trends over time, and analyze performance improvements through interactive graphs.

## Features
- CSV Upload: Users can upload CSV files containing exercise data.
- Data Visualization: Displays date-wise accuracy graphs for different exercises.
- Performance Trends: Generates improvement trends over time.

## Installation

To get started with the ST Project Dashboard, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/Codingis2much4me/ST-Project.git
    ```

2. Navigate to the project directory:
    ```bash
    cd ST-Project
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```


4. Initialize the database:
    ```bash
    python init_db.py
    ```
    This will create the necessary database tables.
   
## Usage
1. To run the ST Project Dashboard locally, use the following command:
    ```bash
    python app.py
    ```
    Open your web browser and navigate to http://localhost:5000 to access the dashboard

2. Click on Sign Up button and create an account .

3. Log in with your credentials to access the dashboard.

4. After logging in click on the Upload New Data button to upload the csv file containing sensor recorded data for your         exercise. We currently support five exercises : Lateral raises, Single arm extensions , Bicep curls, Hammer curls,          Single arm tricep extensions

5. Select your exercise type from the drop down and the date of upload, finally upload your csv file containing the data and click on Upload Exercise Data button.

6. Then go back to dashboard and click on the view button corresponding to your exercise type, you can see the graph showcasing your progress over time and individual 3D data plots showing your accelerometer and gyroscope data along with the golden data.

### CSV File Format

The uploaded CSV files should follow this structure:

| Time [s]  | Acc_X [g] | Acc_Y [g] | Acc_Z [g] | Gyro_X [dps] | Gyro_Y [dps] | Gyro_Z [dps] |
|-----------|----------|----------|----------|-------------|-------------|-------------|
| 2.692948  | 0.385032 | 0.918904 | 0.025864 | -0.280000   | -0.980000   | -0.420000   |
| 2.693074  | 0.382104 | 0.919880 | 0.025864 | -0.280000   | -0.980000   | -0.420000   |
| 2.693200  | 0.385520 | 0.919392 | 0.023912 | -0.280000   | -0.980000   | -0.420000   |
| 2.693326  | 0.383080 | 0.920368 | 0.022448 | -0.140000   | -0.980000   | -0.420000   |
| 2.693452  | 0.385520 | 0.922808 | 0.026352 | -0.140000   | -1.120000   | -0.280000   |
| 2.693578  | 0.389912 | 0.920368 | 0.028304 | -0.140000   | -1.120000   | -0.280000   |
| 2.693704  | 0.380152 | 0.920856 | 0.024888 | -0.140000   | -1.120000   | -0.280000   |
| 2.693830  | 0.385520 | 0.918904 | 0.026840 | -0.140000   | -1.120000   | -0.280000   |
| ...       | ...      | ...      | ...      | ...         | ...         | ...         |

The data is collected using the **STEVAL-MKBOXPRO** wearable sensor kit, which includes an accelerometer and gyroscope to track movement patterns for various exercises. The system processes these readings to visualize accuracy and improvement trends in the dashboard.

For demo you can try uploading files from the synthetic_data_latreal_raises folder.
