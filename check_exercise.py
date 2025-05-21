from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    exercise = Exercise.query.get(6)
    if exercise:
        print(f"\nExercice {exercise.id} :")
        print("-" * 50)
        print(f"Titre: {exercise.title}")
        print(f"Type: {exercise.exercise_type}")
        print("Contenu brut:")
        print(exercise.content)
        print("\nContenu parsé:")
        content = exercise.get_content()
        print(json.dumps(content, indent=2, ensure_ascii=False))
    else:
        print("Exercice non trouvé")
