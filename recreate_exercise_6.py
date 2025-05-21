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
    # Supprimer l'exercice 6 s'il existe
    exercise = Exercise.query.get(6)
    if exercise:
        db.session.delete(exercise)
        db.session.commit()
        print("Ancien exercice supprimé")
    
    # Créer un nouvel exercice
    new_exercise = Exercise(
        id=6,  # Forcer l'ID à 6
        title="Multiplier et diviser par 10, 100, 1000...",
        description="Comprendre les règles de multiplication et division par 10, 100, 1000...",
        exercise_type="qcm",
        teacher_id=1,
        content=json.dumps(content)
    )
    
    db.session.add(new_exercise)
    db.session.commit()
    print("Nouvel exercice créé avec succès !")
    
    # Vérifier le contenu
    exercise = Exercise.query.get(6)
    print("\nContenu de l'exercice :")
    print(json.dumps(json.loads(exercise.content), indent=2, ensure_ascii=False))
