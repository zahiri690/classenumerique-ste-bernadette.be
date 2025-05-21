from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    exercise = Exercise.query.filter_by(exercise_type='fill_in_blanks').first()
    if exercise:
        print(f"ID: {exercise.id}")
        print(f"Title: {exercise.title}")
        print(f"Content: {exercise.content}")
        print("\nParsed content:")
        print(json.dumps(exercise.get_content(), indent=2))
    else:
        print("No fill_in_blanks exercise found")
