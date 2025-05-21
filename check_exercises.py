from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    exercises = Exercise.query.all()
    print("\nListe des exercices :")
    print("-" * 50)
    for exercise in exercises:
        print(f"\nTitre: {exercise.title}")
        print(f"Type: {exercise.exercise_type}")
        content = exercise.get_content()
        if content:
            print("Contenu:", json.dumps(content, indent=2, ensure_ascii=False))
        else:
            print("Pas de contenu")
