from flask import Flask
from models import db, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Afficher les colonnes de la table Exercise
    print("Colonnes de la table Exercise:")
    for column in Exercise.__table__.columns:
        print(f"- {column.name}: {column.type}")
