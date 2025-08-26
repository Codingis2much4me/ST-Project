from model import benchmark_models_with_cv

# List of exercises
exercises = ['Lateral raises', 'Sidearm extensions', 'Bicep curls', 'Hammer curls', 'Single arm tricep extensions']

# Train and save models for all exercises
for exercise in exercises:
    print(f"Training model for {exercise}...")
    benchmark_models_with_cv(exercise)
    print(f"Model for {exercise} saved.\n")