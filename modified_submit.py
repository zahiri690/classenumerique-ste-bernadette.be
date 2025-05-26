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

from flask import current_app

@bp.route('/exercise/<int:exercise_id>')
@login_required
def view_exercise(exercise_id):
    current_app.logger.info(f"[View Exercise] Accessing exercise {exercise_id}")
    exercise = db.get_or_404(Exercise, exercise_id)
    current_app.logger.info(f"[View Exercise] Exercise type: {exercise.exercise_type}")
    current_app.logger.info(f"[View Exercise] Raw content: {exercise.content}")
    
    # Get the latest attempt for this exercise by the current user
    attempt = ExerciseAttempt.query.filter_by(
        exercise_id=exercise_id,
        student_id=current_user.id
    ).order_by(ExerciseAttempt.created_at.desc()).first()
    
    # Get exercise content
    content = exercise.get_content()
    current_app.logger.info(f"[View Exercise] Raw content: {exercise.content}")
    current_app.logger.info(f"[View Exercise] Parsed content: {content}")
    
    if exercise.exercise_type == 'qcm':
        if not content:
            content = {'questions': []}
        elif isinstance(content, str):
            content = json.loads(content)
        
        current_app.logger.info(f"[View QCM] Content structure: {json.dumps(content, indent=2)}")
        
        # Vérifier la structure des questions
        if 'questions' in content:
            for i, q in enumerate(content['questions']):
                current_app.logger.info(f"[View QCM] Question {i}: {q}")
    
    # Debug QCM content
    if exercise.exercise_type == 'qcm':
        current_app.logger.info(f"[View Exercise] QCM content structure: {json.dumps(content, indent=2)}")
        if not content or 'questions' not in content:
            current_app.logger.warning("[View Exercise] QCM content is missing or invalid")
            content = {'questions': []}
    
    # Initialize content if needed
    if not content:
        current_app.logger.warning("[View Exercise] No content found, initializing empty dict")
        content = {}
    
    # Handle word search content
    if exercise.exercise_type == 'word_search':
        current_app.logger.info(f"[View Exercise] Word Search content: {content}")
        if 'grid' not in content or 'words' not in content:
            current_app.logger.warning("[View Exercise] Missing grid or words, creating default content")
            # Default grid size
            grid_size = 10
            grid = [['' for _ in range(grid_size)] for _ in range(grid_size)]
            content = {
                'grid': grid,
                'words': []
            }
        else:
            current_app.logger.info(f"[View Exercise] Grid size: {len(content['grid'])}x{len(content['grid'][0])}")
            current_app.logger.info(f"[View Exercise] Words: {content['words']}")
    
    # Render the appropriate template based on exercise type
    template = f'exercise_types/{exercise.exercise_type}.html'
    current_app.logger.info(f"[View Exercise] Using template: {template}")
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
            if key.startswith('answer_'):
                question_index = int(key.split('_')[1])
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

    elif exercise.exercise_type == 'word_search':
        answers = {}
        found_words = []
        for key, value in request.form.items():
            if key.startswith('word_'):
                word_index = int(key.split('_')[1])
                if value:  # Only count non-empty responses
                    found_words.append(value.strip().upper())
        
        # Calculate score
        correct_count = 0
        total_words = len(content['words'])
        for word in content['words']:
            if word.upper() in found_words:
                correct_count += 1
        
        score = (correct_count / total_words) * 100 if total_words > 0 else 0
        answers = {'found_words': found_words}

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
            question_count = len(request.form.getlist('questions[]'))
            
            current_app.logger.info(f"[Edit QCM] Processing {question_count} questions")
            
            for i in range(question_count):
                question_text = request.form.getlist('questions[]')[i]
                choices = request.form.getlist(f'choices[{i}][]')
                correct_answer = request.form.get(f'correct_answers[{i}]', '0')
                
                current_app.logger.info(f"[Edit QCM] Question {i}: {question_text}")
                current_app.logger.info(f"[Edit QCM] Choices {i}: {choices}")
                current_app.logger.info(f"[Edit QCM] Correct answer {i}: {correct_answer}")
                
                if question_text and choices:
                    question = {
                        'text': question_text,
                        'choices': choices,
                        'correct_answer': int(correct_answer)
                    }
                    questions.append(question)
            
            content = {'questions': questions}
            current_app.logger.info(f"[Edit QCM] Final content: {json.dumps(content, indent=2)}")
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
        elif exercise.exercise_type == 'pairs':
            # Récupérer les paires depuis le formulaire
            pairs = []
            question_count = int(request.form.get('question_count', 0))
            
            for i in range(question_count):
                first = request.form.get(f'pair_{i}_first')
                second = request.form.get(f'pair_{i}_second')
                if first and second:  # Ne garder que les paires complètes
                    pairs.append({'first': first, 'second': second})
            
            # Créer le contenu de l'exercice
            content = {
                'pairs': pairs
            }
            
            exercise.content = json.dumps(content)
            
        elif exercise.exercise_type == 'word_search':
            # Récupérer les mots et la taille de la grille
            words = request.form.getlist('words[]')
            grid_size = int(request.form.get('grid_size', 10))
            
            # Générer la grille de mots mêlés
            from utils.word_search import generate_word_search
            result = generate_word_search(words, grid_size, grid_size)
            
            if result:
                content = {
                    'grid': result['grid'],
                    'words': result['words'],
                    'word_positions': result['word_positions']
                }
            else:
                # En cas d'échec, créer une grille vide
                content = {
                    'grid': [['' for _ in range(grid_size)] for _ in range(grid_size)],
                    'words': words,
                    'word_positions': {}
                }
            
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
    template = f'exercise_types/{exercise.exercise_type}_edit.html'
    return render_template(template, exercise=exercise, content=content)

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

@bp.route('/exercise/<int:exercise_id>/stats')
@login_required
def exercise_stats(exercise_id):
    exercise = db.get_or_404(Exercise, exercise_id)
    
    # Vérifier si l'utilisateur est un enseignant
    if not current_user.is_teacher:
        flash('Vous n\'avez pas la permission de voir les statistiques.', 'danger')
        return redirect(url_for('exercise.view_exercise', exercise_id=exercise_id))
    
    # Récupérer toutes les tentatives pour cet exercice avec les informations des étudiants
    attempts = ExerciseAttempt.query.filter_by(exercise_id=exercise_id)\
        .join(ExerciseAttempt.student)\
        .order_by(ExerciseAttempt.created_at.desc())\
        .all()
    
    # Calculer les statistiques
    total_attempts = len(attempts)
    if total_attempts > 0:
        avg_score = sum(attempt.score for attempt in attempts) / total_attempts
    else:
        avg_score = 0
    
    # Compter les tentatives par score
    score_distribution = {}
    for attempt in attempts:
        score_range = (attempt.score // 10) * 10  # Arrondir au plus proche multiple de 10
        score_distribution[score_range] = score_distribution.get(score_range, 0) + 1
    
    return render_template('exercise_stats.html',
                         exercise=exercise,
                         total_attempts=total_attempts,
                         avg_score=avg_score,
                         score_distribution=score_distribution,
                         attempts=attempts)

def init_app(app):
    app.register_blueprint(bp)
