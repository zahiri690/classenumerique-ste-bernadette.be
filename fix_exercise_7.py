from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Récupérer l'exercice 6
    exercise = Exercise.query.get(6)
    if not exercise:
        exercise = Exercise(
            title="Multiplier et diviser par 10, 100, 1000...",
            description="Comprendre les règles de multiplication et division par 10, 100, 1000...",
            exercise_type="qcm",
            teacher_id=1
        )
    
    # Mettre à jour le contenu
    content = {
            'questions': [
                {
                    'question': 'Multiplier un nombre par 10',
                    'options': [
                        'On ajoute un zéro à droite',
                        'On déplace la virgule d\'un rang vers la droite',
                        'On ajoute un zéro à gauche',
                        'On multiplie chaque chiffre par 10'
                    ],
                    'correct': 1
                },
                {
                    'question': 'Multiplier un nombre par 100',
                    'options': [
                        'On ajoute deux zéros à droite',
                        'On déplace la virgule de deux rangs vers la droite',
                        'On ajoute deux zéros à gauche',
                        'On multiplie chaque chiffre par 100'
                    ],
                    'correct': 1
                }
            ]
        }
    
    exercise.content = json.dumps(content)
    db.session.add(exercise)
    db.session.commit()
    print("Exercice créé avec succès !")
    print("\nNouveau contenu :")
    print(json.dumps(exercise.get_content(), indent=2))
