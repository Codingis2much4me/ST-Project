import os
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib  # For saving and loading models
import logging  # For logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define directories
TRAINING_DATA_DIR = "training_data"
MODEL_DIR = "models"

# Ensure the model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)

# Function to create time-series features
def create_time_series_features(df, window_size=5):
    logging.info("Creating time-series features...")
    feature_cols = df.columns.difference(["Time [s]", "label"])
    for col in feature_cols:
        for lag in range(1, window_size + 1):
            df[f"{col}_lag{lag}"] = df[col].shift(lag)
    df.fillna(0, inplace=True)  # Handle NaN values from shifting
    
    # Rolling statistics
    for col in feature_cols:
        df[f"{col}_rolling_mean"] = df[col].rolling(window=window_size).mean().fillna(0)
        df[f"{col}_rolling_std"] = df[col].rolling(window=window_size).std().fillna(0)
    
    logging.info("Time-series features created.")
    return df

# Load and preprocess training data
def load_training_data(exercise_name):
    logging.info(f"Loading training data for {exercise_name}...")
    proper_form_path = os.path.join(TRAINING_DATA_DIR, exercise_name, "proper_form")
    improper_form_path = os.path.join(TRAINING_DATA_DIR, exercise_name, "improper_form")
    
    proper_dfs = [pd.read_csv(os.path.join(proper_form_path, file)) for file in os.listdir(proper_form_path) if file.endswith(".csv")]
    improper_dfs = [pd.read_csv(os.path.join(improper_form_path, file)) for file in os.listdir(improper_form_path) if file.endswith(".csv")]
    
    proper_df = pd.concat(proper_dfs, ignore_index=True)
    improper_df = pd.concat(improper_dfs, ignore_index=True)
    
    proper_df["label"] = 1  # 1 for proper form
    improper_df["label"] = 0  # 0 for improper form
    
    data = pd.concat([proper_df, improper_df], ignore_index=True)
    data = create_time_series_features(data)
    
    logging.info(f"Training data for {exercise_name} loaded and preprocessed.")
    return data

def train_decision_tree(exercise_name):
    logging.info(f"Training Decision Tree model for {exercise_name}...")
    
    # Load and preprocess the training data
    logging.info("Loading and preprocessing data...")
    data = load_training_data(exercise_name)
    feature_cols = data.columns.difference(["Time [s]", "label"])
    X = data[feature_cols]
    y = data["label"]
    
    # Split the data into training and testing sets
    logging.info("Splitting data into training and testing sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Initialize the Decision Tree model with default parameters
    logging.info("Initializing Decision Tree model with default parameters...")
    dt_model = DecisionTreeClassifier(random_state=42)
    
    # Train the model
    logging.info("Training the model...")
    dt_model.fit(X_train, y_train)
    
    # Evaluate the model on the test set
    logging.info("Evaluating the model on the test set...")
    y_pred = dt_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    logging.info(f"Training Accuracy for {exercise_name}: {accuracy * 100:.2f}%")
    
    # Save the model to disk
    model_path = os.path.join(MODEL_DIR, f"{exercise_name}_model.pkl")
    joblib.dump(dt_model, model_path)
    logging.info(f"Model saved to {model_path}")
    
    return dt_model

# Load a pre-trained model
def load_model(exercise_name):
    logging.info(f"Loading pre-trained model for {exercise_name}...")
    model_path = os.path.join(MODEL_DIR, f"{exercise_name}_model.pkl")
    if os.path.exists(model_path):
        return joblib.load(model_path)
    else:
        raise FileNotFoundError(f"No model found for exercise: {exercise_name}")

# Predict form correctness
def predict_form(model, df):
    logging.info("Predicting form correctness...")
    df = create_time_series_features(df)
    feature_cols = df.columns.difference(["Time [s]", "label"])
    predictions = model.predict(df[feature_cols])
    logging.info("Form correctness predictions completed.")
    return predictions