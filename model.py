
import os
import pandas as pd
import numpy as np
import joblib
import logging
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define directories
TRAINING_DATA_DIR = "training_data"
MODEL_DIR = "models"

# Ensure the model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)
BEST_MODELS_FILE = os.path.join(MODEL_DIR, "best_models.csv")


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


# ---------------- Custom CV Split ----------------
class BalancedTimeSeriesSplit:
    def __init__(self, n_splits=5):
        self.n_splits = n_splits

    def split(self, X, y, groups=None):
        proper_idx = np.where(y == 1)[0]
        improper_idx = np.where(y == 0)[0]
        proper_idx.sort()
        improper_idx.sort()

        proper_chunk = len(proper_idx) // self.n_splits
        improper_chunk = len(improper_idx) // self.n_splits

        for i in range(self.n_splits):
            proper_test = proper_idx[i*proper_chunk:(i+1)*proper_chunk]
            improper_test = improper_idx[i*improper_chunk:(i+1)*improper_chunk]
            test_idx = np.concatenate([proper_test, improper_test])
            train_idx = np.setdiff1d(np.arange(len(y)), test_idx)
            yield train_idx, test_idx

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits

# ---------------- Train & Benchmark Models ----------------
def benchmark_models_with_cv(exercise_name, cv_folds=3):
    data = load_training_data(exercise_name)
    feature_cols = data.columns.difference(["Time [s]", "label"])
    X, y = data[feature_cols], data["label"]

    # Custom 80/20 split with contiguous blocks (10% proper + 10% improper in test)
    proper_idx = np.where(y == 1)[0]
    improper_idx = np.where(y == 0)[0]
    test_proper = proper_idx[int(0.9*len(proper_idx)):]
    test_improper = improper_idx[int(0.9*len(improper_idx)):]
    test_idx = np.concatenate([test_proper, test_improper])
    train_idx = np.setdiff1d(np.arange(len(y)), test_idx)

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    models = {
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "Extra Trees": ExtraTreesClassifier(n_estimators=100, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=5)
    }

    results = []
    btscv = BalancedTimeSeriesSplit(n_splits=cv_folds)

    for name, model in models.items():
        logging.info(f"Evaluating {name}...")

        cv_scores = cross_val_score(model, X_train, y_train, cv=btscv, scoring="accuracy", error_score="raise")
        cv_mean, cv_std = cv_scores.mean() * 100, cv_scores.std() * 100

        model.fit(X_train, y_train)

        train_acc = accuracy_score(y_train, model.predict(X_train)) * 100
        test_acc = accuracy_score(y_test, model.predict(X_test)) * 100

        results.append({
            "Model": name,
            "Train Accuracy": round(train_acc, 2),
            "CV Mean Accuracy": round(cv_mean, 2),
            "CV StdDev": round(cv_std, 2),
            "Test Accuracy": round(test_acc, 2)
        })

        model_path = os.path.join(MODEL_DIR, f"{exercise_name}_{name.replace(' ', '_').lower()}.pkl")
        joblib.dump(model, model_path)

    results_df = pd.DataFrame(results).sort_values(by="Test Accuracy", ascending=False)
    print("\nModel Benchmark Results:")
    print(results_df.to_string(index=False))

    # Save best model
    best_model_name = results_df.iloc[0]["Model"]
    best_model_path = os.path.join(MODEL_DIR, f"{exercise_name}_{best_model_name.replace(' ', '_').lower()}.pkl")
    final_model_path = os.path.join(MODEL_DIR, f"{exercise_name}_best.pkl")
    joblib.dump(joblib.load(best_model_path), final_model_path)

    logging.info(f"Best model for {exercise_name}: {best_model_name} (saved as {final_model_path})")
    return results_df


def load_model(exercise_name):
    logging.info(f"Loading best pre-trained model for {exercise_name}...")
    if not os.path.exists(BEST_MODELS_FILE):
        raise FileNotFoundError("No best_models.csv found. Run benchmark_models_with_cv first.")
    
    best_models_df = pd.read_csv(BEST_MODELS_FILE)
    row = best_models_df[best_models_df["Exercise"] == exercise_name]
    if row.empty:
        raise FileNotFoundError(f"No best model entry found for {exercise_name}.")
    
    best_model_file = row.iloc[0]["BestModelFile"]
    model_path = os.path.join(MODEL_DIR, best_model_file)
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    return joblib.load(model_path)


def predict_form(model, df):
    logging.info("Predicting form correctness...")
    df = create_time_series_features(df)
    feature_cols = df.columns.difference(["Time [s]", "label"])
    predictions = model.predict(df[feature_cols])
    logging.info("Form correctness predictions completed.")
    return predictions