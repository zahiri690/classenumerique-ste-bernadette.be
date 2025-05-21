from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

content = {
    'questions': [
        {
            'text': 'Multiplier un nombre par 10',
            'choices': [
                'On ajoute un zéro à droite',
                'On déplace la virgule d\'un rang vers la droite',
                'On ajoute un zéro à gauche',
                'On multiplie chaque chiffre par 10'
            ],
            'correct_answer': 1
        },
        {
            'text': 'Multiplier un nombre par 100',
            'choices': [
                'On ajoute deux zéros à droite',
                'On déplace la virgule de deux rangs vers la droite',
                'On ajoute deux zéros à gauche',
                'On multiplie chaque chiffre par 100'
            ],
            'correct_answer': 1
        }
    ]
}

with app.app_context():
    # Récupérer l'exercice 6
    exercise = Exercise.query.get(6)
    if exercise:
        # Mettre à jour uniquement le contenu
        exercise.content = json.dumps(content)
        db.session.commit()
        print("Contenu de l'exercice mis à jour avec succès !")
    else:
        print("Exercice 6 non trouvé")
