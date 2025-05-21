from app import app, db, User
from werkzeug.security import generate_password_hash

def reset_database():
    with app.app_context():
        # Supprimer toutes les tables
        db.drop_all()
        
        # Recréer toutes les tables
        db.create_all()
        
        # Créer un compte admin par défaut
        admin = User(
            email='admin1@example.com',
            name='Admin',
            username='admin1',  # Ajout du champ username requis
            role='admin'  # Définir le rôle comme admin
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        
        print("Base de données réinitialisée avec succès !")

if __name__ == '__main__':
    reset_database()
