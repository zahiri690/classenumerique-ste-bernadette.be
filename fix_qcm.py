from flask import Flask
from models import db, Exercise

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Contenu correct pour l'exercice 2
correct_content = {
    "questions": [
        {
            "text": "0,07 × 900 =",
            "choices": ["0.63", "6.3", "63"],
            "correct_answer": 2
        },
        {
            "text": "3,5 × 10 =",
            "choices": ["35", "3.50", "0.35"],
            "correct_answer": 0
        }
    ]
}

with app.app_context():
    # Récupérer l'exercice 2
    exercise = Exercise.query.get(2)
    if exercise and exercise.exercise_type == 'qcm':
        print(f"Mise à jour de l'exercice {exercise.id}")
        print(f"Ancien contenu : {exercise.content}")
        exercise.content = str(correct_content)
        db.session.commit()
        print(f"Nouveau contenu : {exercise.content}")
