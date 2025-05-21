from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Exercise, ExerciseAttempt
from sqlalchemy import desc
import json

bp = Blueprint('exercise', __name__)

@bp.route('/exercise_library')
@login_required
def exercise_library():
    exercises = Exercise.query.order_by(desc(Exercise.created_at)).all()
    return render_template('exercise_library.html', exercises=exercises)

@bp.route('/exercise/<int:exercise_id>')
@login_required
def view_exercise(exercise_id):
    exercise = db.get_or_404(Exercise, exercise_id)
    
    # Get the latest attempt for this exercise by the current user
    attempt = ExerciseAttempt.query.filter_by(
        exercise_id=exercise_id,
        student_id=current_user.id
    ).order_by(ExerciseAttempt.created_at.desc()).first()
    
    # Get exercise content
    content = exercise.get_content()
    
    # Render the appropriate template based on exercise type
    template = f'exercise_types/{exercise.exercise_type}.html'
    return render_template(template,
                         exercise=exercise,
                         content=content,
                         attempt=attempt)

@bp.route('/exercise/<int:exercise_id>/submit', methods=['POST'])
@login_required
def submit_answer(exercise_id):
    exercise = db.get_or_404(Exercise, exercise_id)
    content = exercise.get_content()
    
    if exercise.exercise_type == 'qcm':
        answers = {}
        for key, value in request.form.items():
            if key.startswith('answer[') and key.endswith(']'):
                question_index = int(key[7:-1])  # Extraire l'index entre answer[ et ]
                answers[question_index] = int(value)
        
        # Calculate score
        correct_count = 0
        total_questions = len(content['questions'])
        for i, question in enumerate(content['questions']):
            if i in answers and answers[i] == question['correct_answer']:
                correct_count += 1
        
        score = (correct_count / total_questions) * 100

    elif exercise.exercise_type == 'fill_in_blanks':
        answers = {}
        for key, value in request.form.items():
            if key.startswith('answer_'):
                blank_index = int(key.split('_')[1])
                answers[blank_index] = value.strip().lower()  # Convertir en minuscules
        
        # Calculate score
        correct_count = 0
        total_blanks = len(content['phrases'])
        for i, phrase in enumerate(content['phrases']):
            if i in answers and answers[i] == phrase['answer'].lower():  # Comparer en minuscules
                correct_count += 1
        
        score = (correct_count / total_blanks) * 100 if total_blanks > 0 else 0

    elif exercise.exercise_type == 'pairs':
        answers = {}
        for key, value in request.form.items():
            if key.startswith('pair_'):
                pair_index = int(key.split('_')[1])
                if value:  # Only count non-empty responses
                    answers[pair_index] = int(value)
        
        # Calculate score
        correct_count = 0
        total_pairs = len(content['pairs'])
        for i, pair in enumerate(content['pairs']):
            if i in answers and answers[i] == i:  # Correct if indices match
                correct_count += 1
        
        score = (correct_count / total_pairs) * 100

    else:
        return jsonify({'error': 'Type d\'exercice non pris en charge'}), 400

    # Create attempt record
    attempt = ExerciseAttempt(
        exercise_id=exercise_id,
        student_id=current_user.id,
        score=score,
        answers=json.dumps(answers)
    )
    db.session.add(attempt)
    db.session.commit()

    flash(f'Exercice soumis avec succès ! Score : {score:.1f}%', 'success')
    return redirect(url_for('exercise.view_exercise', exercise_id=exercise_id))

@bp.route('/exercise/<int:exercise_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_exercise(exercise_id):
    exercise = db.get_or_404(Exercise, exercise_id)
    
    # Check if user is the teacher who created this exercise
    if not current_user.is_teacher or current_user.id != exercise.teacher_id:
        flash('Vous n\'avez pas la permission de modifier cet exercice.', 'danger')
        return redirect(url_for('exercise.view_exercise', exercise_id=exercise_id))
    
    if request.method == 'POST':
        exercise.title = request.form['title']
        exercise.description = request.form['description']
        
        if exercise.exercise_type == 'qcm':
            # Formater les données QCM
            questions = []
            for i in range(len(request.form.getlist('questions[]'))):
                question = {
                    'text': request.form.getlist('questions[]')[i],
                    'options': request.form.getlist(f'options[{i}][]'),
                    'correct_answer': int(request.form.get(f'correct_answers[{i}]', 0))
                }
                questions.append(question)
            content = {'questions': questions}
            exercise.content = json.dumps(content)
        elif exercise.exercise_type == 'fill_in_blanks':
            # Formater les données du texte à trous
            sentences = request.form.getlist('sentences[]')
            phrases = []
            for sentence in sentences:
                # Extraire les mots entre crochets
                import re
                text = re.sub(r'\[([^\]]+)\]', '___', sentence)
                answers = re.findall(r'\[([^\]]+)\]', sentence)
                if answers:  # Ne garder que les phrases avec des trous
                    phrases.append({
                        'text': text,
                        'answer': answers[0]  # Prendre la première réponse pour chaque phrase
                    })
            content = {'phrases': phrases}
            exercise.content = json.dumps(content)
        else:
            exercise.content = request.form['content']
        
        try:
            db.session.commit()
            flash('Exercice modifié avec succès!', 'success')
            return redirect(url_for('exercise.view_exercise', exercise_id=exercise_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue lors de la modification: {str(e)}', 'danger')
    
    # Get exercise content
    content = exercise.get_content()
    return render_template('edit_exercise.html', exercise=exercise, content=content)

@bp.route('/exercise/<int:exercise_id>/delete', methods=['POST'])
@login_required
def delete_exercise(exercise_id):
    exercise = db.get_or_404(Exercise, exercise_id)
    
    # Check if user is the teacher who created this exercise
    if not current_user.is_teacher or current_user.id != exercise.teacher_id:
        flash('Vous n\'avez pas la permission de supprimer cet exercice.', 'danger')
        return redirect(url_for('exercise.exercise_library'))
    
    try:
        db.session.delete(exercise)
        db.session.commit()
        flash('Exercice supprimé avec succès!', 'success')
    except:
        db.session.rollback()
        flash('Une erreur est survenue lors de la suppression.', 'danger')
    
    return redirect(url_for('exercise.exercise_library'))

def init_app(app):
    app.register_blueprint(bp)
