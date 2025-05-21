from flask import Flask
from models import db, User, Exercise
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Supprimer tous les utilisateurs et exercices existants
    Exercise.query.delete()
    User.query.delete()
    db.session.commit()

    # Créer un utilisateur enseignant
    teacher = User(
        username="Mr ZAHIRI",
        email="mr.zahiri@gmail.com",
        role="teacher"
    )
    teacher.set_password("password123")
    db.session.add(teacher)
    db.session.commit()

    # 1. Exercice à trous sur les nombres décimaux
    fill_blanks = Exercise(
        title=" Exercice1:Nombres décimaux - Exercice à trous",
        description="Complétez les phrases avec les bons nombres.",
        exercise_type="fill_in_blanks",
        content=json.dumps({
            "sentences": [
                {"text": "Dans 3,45 le chiffre des dixièmes est", "answer": "4"},
                {"text": "Dans 3,45 le chiffre des centièmes est", "answer": "5"},
                {"text": "3,45 = _____ unités et 45 centièmes", "answer": "3"},
                {"text": "3,45 = _____ dixièmes", "answer": "34"},
                {"text": "3,45 = _____ centièmes", "answer": "345"}
            ],
            "available_words": ["3", "4", "5", "34", "345"]
        }),
        teacher_id=teacher.id
    )
    db.session.add(fill_blanks)

    # 2. QCM sur les nombres décimaux
    qcm = Exercise(
        title="Exercice2:Nombres décimaux - QCM",
        description="Choisissez la bonne réponse pour chaque calcul.",
        exercise_type="qcm",
        content=json.dumps({
            "questions": [
                {
                    "text": "0,07 × 900 =",
                    "choices": ["0.63", "6.3", "63"],
                    "correct_answer": 2
                },
                {
                    "text": "3,5 × 0,2 =",
                    "choices": ["0.7", "7", "0.07"],
                    "correct_answer": 0
                },
                {
                    "text": "4,8 ÷ 100 =",
                    "choices": ["0.048", "0.48", "4.80"],
                    "correct_answer": 0
                }
            ]
        }),
        teacher_id=teacher.id
    )
    db.session.add(qcm)

    # 3. Exercice d'appariement sur les nombres décimaux
    pairs = Exercise(
        title="Exercice3:Nombres décimaux - Appariement",
        description="Associez chaque nombre décimal à son écriture en lettres.",
        exercise_type="pairs",
        content=json.dumps({
            "left_items": ["3,14", "0,5", "2,08", "0,25"],
            "right_items": [
                "trois unités et quatorze centièmes",
                "cinq dixièmes",
                "deux unités et huit centièmes",
                "vingt-cinq centièmes"
            ],
            "correct_pairs": [[0, 0], [1, 1], [2, 2], [3, 3]]
        }),
        teacher_id=teacher.id
    )
    db.session.add(pairs)
    db.session.commit()

    # 4. Exercice de glisser-déposer sur les nombres décimaux
    drag_drop = Exercise(
        title="Exercice4:Nombres décimaux - Glisser-déposer",
        description="Placez les nombres décimaux dans l'ordre croissant.",
        exercise_type="drag_and_drop",
        content=json.dumps({
            "draggable_items": ["0,8", "0,08", "0,85", "0,9"],
            "drop_zones": [
                "Premier nombre",
                "Deuxième nombre",
                "Troisième nombre",
                "Quatrième nombre"
            ],
            "correct_order": [1, 0, 2, 3]
        }),
        teacher_id=teacher.id
    )
    db.session.add(drag_drop)

    db.session.commit()
    print("Exercices créés avec succès !")
    print("\nIdentifiants de connexion enseignant :")
    print("Email : mr.zahiri@gmail.com")
    print("Password : password123")
