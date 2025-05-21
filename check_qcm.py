from flask import Flask
from models import db, Exercise

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Récupérer tous les exercices de type QCM
    qcm_exercises = Exercise.query.filter_by(exercise_type='qcm').all()
    
    print("Liste des exercices QCM :")
    print("-" * 50)
    
    for exercise in qcm_exercises:
        print(f"\nExercice {exercise.id} :")
        print(f"Titre: {exercise.title}")
        print(f"Type: {exercise.exercise_type}")
        print(f"Contenu brut:\n{exercise.content}")
        try:
            content = exercise.get_content()
            print(f"\nContenu parsé:\n{content}")
        except Exception as e:
            print(f"\nErreur de parsing: {str(e)}")
