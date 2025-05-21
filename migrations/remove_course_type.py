from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db

def remove_course_type():
    # Créer une connexion directe à la base de données
    with db.session.begin():
        # Vérifier si la colonne existe
        result = db.session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='course'"))
        create_stmt = result.scalar()
        
        if create_stmt and 'type' in create_stmt:
            # Créer une nouvelle table sans la colonne type
            db.session.execute(text("""
                CREATE TABLE course_new (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    content TEXT,
                    class_id INTEGER NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY (class_id) REFERENCES class (id)
                )
            """))
            
            # Copier les données
            db.session.execute(text("""
                INSERT INTO course_new (id, title, content, class_id, created_at)
                SELECT id, title, content, class_id, created_at
                FROM course
            """))
            
            # Supprimer l'ancienne table
            db.session.execute(text("DROP TABLE course"))
            
            # Renommer la nouvelle table
            db.session.execute(text("ALTER TABLE course_new RENAME TO course"))
            
            # Recréer les index et contraintes
            db.session.execute(text("""
                CREATE INDEX ix_course_class_id ON course (class_id);
            """))
            
            print("Colonne 'type' supprimée avec succès de la table 'course'")
        else:
            print("La colonne 'type' n'existe pas dans la table 'course'")

if __name__ == '__main__':
    # Créer une application Flask minimale
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialiser l'extension
    db.init_app(app)
    
    # Exécuter la migration dans le contexte de l'application
    with app.app_context():
        remove_course_type()
