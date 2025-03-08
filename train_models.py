from model import train_decision_tree

# List of exercises
exercises = ['Lateral raises', 'Sidearm extensions', 'Bicep curls', 'Hammer curls', 'Single arm tricep extensions']

# Train and save models for all exercises
for exercise in exercises:
    print(f"Training model for {exercise}...")
    train_decision_tree(exercise)
    print(f"Model for {exercise} saved.\n")