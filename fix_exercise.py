from flask import Flask
from models import db, Exercise
import json
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    exercise = Exercise.query.filter_by(exercise_type='fill_in_blanks').first()
    if exercise:
        content = json.loads(exercise.content)
        
        # Si le contenu est déjà dans le nouveau format
        if 'sentences' in content:
            # Remplacer [...] par ___ dans les phrases existantes
            content['sentences'] = [s.replace('[...]', '___') for s in content['sentences']]
        else:
            # Convertir l'ancien format en nouveau format
            sentences = content['text'].strip().split('\n')
            sentences = [s.strip() for s in sentences if s.strip()]
            sentences = [s.replace('[...]', '___') for s in sentences]
            content = {
                'sentences': sentences,
                'words': content['answers']
            }
        
        # Sauvegarder le nouveau format
        exercise.content = json.dumps(content)
        db.session.commit()
        
        print("Exercice mis à jour avec succès!")
        print("\nNouveau contenu:")
        print(json.dumps(exercise.get_content(), indent=2))
    else:
        print("No fill_in_blanks exercise found")
