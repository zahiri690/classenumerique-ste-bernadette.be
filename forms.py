from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, validators

class ExerciseForm(FlaskForm):
    title = StringField('Titre', validators=[validators.DataRequired()])
    description = TextAreaField('Description', validators=[validators.DataRequired()])
    exercise_type = SelectField('Type d\'exercice', choices=[
        ('qcm', 'QCM'),
        ('fill_in_blanks', 'Texte à trous'),
        ('pairs', 'Appariement'),
        ('word_search', 'Mots mêlés')
    ], validators=[validators.DataRequired()])

