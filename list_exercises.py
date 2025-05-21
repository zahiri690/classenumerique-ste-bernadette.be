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
    for ex in exercises:
        print(f"ID: {ex.id}")
        print(f"Titre: {ex.title}")
        print(f"Type: {ex.exercise_type}")
        print("Contenu:")
        try:
            content = json.loads(ex.content)
            print(json.dumps(content, indent=2, ensure_ascii=False))
        except:
            print("(Contenu invalide)")
        print("-" * 50)
