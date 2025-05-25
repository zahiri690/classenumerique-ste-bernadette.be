from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

from extensions import db

# Table d'association pour les étudiants et les classes
student_class_association = db.Table('student_class',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id', name='fk_student_class'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id', name='fk_class_student'), primary_key=True)
)

# Table d'association entre Course et Exercise
course_exercise = db.Table('course_exercise',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('exercise_id', db.Integer, db.ForeignKey('exercise.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin', 'teacher', 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    classes_enrolled = db.relationship('Class', secondary=student_class_association, back_populates='students')
    classes_teaching = db.relationship('Class', backref='teacher', lazy=True, foreign_keys='Class.teacher_id')
    exercises = db.relationship('Exercise', backref='teacher', lazy=True)
    exercise_attempts = db.relationship('ExerciseAttempt', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_admin(self):
        return self.role == 'admin'

    def is_enrolled(self, class_id):
        """Check if the user is enrolled in a specific class."""
        return any(class_obj.id == class_id for class_obj in self.classes_enrolled)

    def get_average_score(self, course_id=None):
        """Obtenir la moyenne des scores pour tous les exercices ou pour un cours spécifique"""
        query = self.exercise_attempts
        if course_id:
            query = query.filter_by(course_id=course_id)
        scores = [attempt.score for attempt in query.all()]
        return sum(scores) / len(scores) if scores else 0
    
    def get_exercise_stats(self, exercise_id):
        """Obtenir les statistiques pour un exercice spécifique"""
        attempts = self.exercise_attempts.filter_by(exercise_id=exercise_id).all()
        if not attempts:
            return None
        scores = [attempt.score for attempt in attempts]
        return {
            'attempts_count': len(attempts),
            'best_score': max(scores),
            'average_score': sum(scores) / len(scores),
            'last_attempt': attempts[-1]
        }

class Class(db.Model):
    __tablename__ = 'class'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_class_teacher'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    access_code = db.Column(db.String(6), unique=True, nullable=False)
    
    # Relations
    students = db.relationship('User', secondary=student_class_association, back_populates='classes_enrolled')
    courses = db.relationship('Course', backref='class_obj', lazy=True, cascade='all, delete-orphan')

class Course(db.Model):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Stocké en JSON
    class_id = db.Column(db.Integer, db.ForeignKey('class.id', name='fk_course_class'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    course_files = db.relationship('CourseFile', backref='course', lazy=True, cascade='all, delete-orphan')
    exercises = db.relationship('Exercise', secondary=course_exercise, back_populates='courses', lazy=True)
    
    def __repr__(self):
        return f'<Course {self.title}>'
    
    def get_student_stats(self, student_id):
        """Obtenir les statistiques d'un élève pour ce cours"""
        attempts = ExerciseAttempt.query.filter_by(
            course_id=self.id,
            student_id=student_id
        ).all()
        
        if not attempts:
            return {
                'exercises_attempted': 0,
                'exercises_completed': 0,
                'average_score': 0,
                'best_exercise': None,
                'needs_improvement': None
            }
        
        # Grouper les tentatives par exercice
        exercise_attempts = {}
        for attempt in attempts:
            if attempt.exercise_id not in exercise_attempts:
                exercise_attempts[attempt.exercise_id] = []
            exercise_attempts[attempt.exercise_id].append(attempt)
        
        # Calculer les meilleures notes pour chaque exercice
        best_scores = {}
        completed_exercises = 0
        total_exercises = len(self.exercises)
        
        for ex_id, ex_attempts in exercise_attempts.items():
            valid_scores = [a.score for a in ex_attempts if a.score is not None]
            if valid_scores:
                best_score = max(valid_scores)
                best_scores[ex_id] = best_score
                if best_score >= 70:  # Considérer un exercice comme complété si score >= 70%
                    completed_exercises += 1
        
        # Trouver le meilleur et le pire exercice
        best_exercise = max(best_scores.items(), key=lambda x: x[1])[0] if best_scores else None
        needs_improvement = min(best_scores.items(), key=lambda x: x[1])[0] if best_scores else None
        
        return {
            'exercises_attempted': len(exercise_attempts),
            'exercises_completed': completed_exercises,
            'total_exercises': total_exercises,
            'average_score': sum(best_scores.values()) / len(best_scores) if best_scores else 0,
            'best_exercise': Exercise.query.get(best_exercise) if best_exercise else None,
            'needs_improvement': Exercise.query.get(needs_improvement) if needs_improvement else None
        }

class Exercise(db.Model):
    __tablename__ = 'exercise'
    
    EXERCISE_TYPES = [
        ('qcm', 'QCM'),
        ('word_search', 'Mots mêlés'),
        ('pairs', 'Association de paires'),
        ('fill_in_blanks', 'Texte à trous'),
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    exercise_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text)  # Stocké en JSON
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_exercise_teacher'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    max_attempts = db.Column(db.Integer, default=None)  # Nombre maximum de tentatives autorisées, None = illimité
    
    # Relations
    courses = db.relationship('Course', secondary=course_exercise, back_populates='exercises', lazy=True)
    attempts = db.relationship('ExerciseAttempt', backref='exercise', lazy=True)
    
    def __repr__(self):
        return f'<Exercise {self.id}: {self.title}>'

    def to_dict(self):
        """Convertit l'exercice en dictionnaire pour la sérialisation JSON."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'exercise_type': self.exercise_type,
            'content': self.get_content()
        }
    
    def get_content(self):
        """Récupère le contenu JSON de l'exercice de manière sécurisée"""
        from flask import current_app
        
        if not self.content:
            current_app.logger.warning(f"[Exercise {self.id}] No content found")
            return None
        
        try:
            content = json.loads(self.content)
            current_app.logger.info(f"[Exercise {self.id}] Successfully loaded JSON content")
            
            # Traitement spécifique selon le type d'exercice
            if self.exercise_type == 'qcm':
                # Vérifier que le contenu a la bonne structure
                if not isinstance(content, dict) or 'questions' not in content:
                    return {
                        'questions': []
                    }
                
                # Vérifier chaque question
                for question in content['questions']:
                    if not isinstance(question, dict):
                        continue
                    
                    # S'assurer que les champs requis sont présents
                    if 'text' not in question:
                        question['text'] = ''
                    if 'choices' not in question:
                        question['choices'] = []
                    if 'correct_answer' not in question:
                        question['correct_answer'] = 0
                    
                    # S'assurer que correct_answer est dans les limites
                    if question['correct_answer'] >= len(question['choices']):
                        question['correct_answer'] = 0
                    
                    # Convertir 'options' en 'choices' si nécessaire (rétro-compatibilité)
                    if 'options' in question:
                        question['choices'] = question.pop('options')
            
            elif self.exercise_type == 'fill_in_blanks':
                # Vérifier que le contenu a la bonne structure
                if not isinstance(content, dict) or 'phrases' not in content:
                    return {
                        'phrases': []
                    }
                
                # Vérifier chaque phrase
                for phrase in content['phrases']:
                    if not isinstance(phrase, dict):
                        continue
                    if 'text' not in phrase:
                        phrase['text'] = ''
                    if 'answer' not in phrase:
                        phrase['answer'] = ''
            
            elif self.exercise_type == 'word_search':
                current_app.logger.info(f"[Exercise {self.id}] Processing word search content: {content}")
                
                # Vérifier que le contenu a la bonne structure
                if not isinstance(content, dict):
                    current_app.logger.warning(f"[Exercise {self.id}] Content is not a dict, creating empty dict")
                    content = {}
                
                # S'assurer que tous les champs requis sont présents
                if 'grid' not in content or not content['grid']:
                    current_app.logger.warning(f"[Exercise {self.id}] Grid is missing or empty, creating 10x10 grid")
                    # Créer une grille vide 10x10 par défaut
                    content['grid'] = [[''] * 10 for _ in range(10)]
                
                if 'words' not in content:
                    current_app.logger.warning(f"[Exercise {self.id}] Words list is missing, creating empty list")
                    content['words'] = []
                
                # Vérifier que la grille est valide
                grid_height = len(content['grid'])
                grid_width = len(content['grid'][0]) if grid_height > 0 else 10
                current_app.logger.info(f"[Exercise {self.id}] Grid dimensions: {grid_height}x{grid_width}")
                
                # S'assurer que toutes les lignes ont la même longueur et contiennent des chaînes
                content['grid'] = [
                    [str(cell) if cell else '' for cell in (row[:grid_width] + [''] * (grid_width - len(row)))]
                    for row in content['grid'][:grid_height]
                ]
                current_app.logger.info(f"[Exercise {self.id}] Final content: {content}")
                    
            elif self.exercise_type == 'pairs':
                current_app.logger.info(f"[Exercise {self.id}] Processing pairs content: {content}")
                
                # Vérifier que le contenu a la bonne structure
                if not isinstance(content, dict):
                    current_app.logger.warning(f"[Exercise {self.id}] Content is not a dict, creating empty dict")
                    content = {}
                
                # S'assurer que pairs est présent et est une liste
                if 'pairs' not in content or not isinstance(content['pairs'], list):
                    current_app.logger.warning(f"[Exercise {self.id}] Pairs list is missing or invalid, creating empty list")
                    content['pairs'] = []
                
                # Vérifier chaque paire
                valid_pairs = []
                for pair in content['pairs']:
                    if isinstance(pair, dict) and 'first' in pair and 'second' in pair:
                        valid_pairs.append({
                            'first': str(pair['first']),
                            'second': str(pair['second'])
                        })
            
                content['pairs'] = valid_pairs
                current_app.logger.info(f"[Exercise {self.id}] Final pairs content: {content}")
                    
            return content
        
        except json.JSONDecodeError as e:
            current_app.logger.error(f"[Exercise {self.id}] JSON decode error: {str(e)}")
            # En cas d'erreur de décodage JSON, retourner un contenu vide
            return {}
        
        except Exception as e:
            current_app.logger.error(f"[Exercise {self.id}] Unexpected error: {str(e)}")
            return {}
    
    def set_content(self, content):
        """Enregistre le contenu de l'exercice"""
        self.content = json.dumps(content)
    
    def get_student_progress(self, student_id):
        """Récupère la progression d'un étudiant sur cet exercice"""
        attempts = ExerciseAttempt.query.filter_by(
            exercise_id=self.id,
            student_id=student_id
        ).order_by(ExerciseAttempt.created_at.desc()).all()
        
        if not attempts:
            return {
                'attempts_count': 0,
                'remaining_attempts': self.max_attempts if self.max_attempts else None,
                'best_score': 0,
                'last_attempt': None,
                'status': 'not_started'
            }
        
        # Calculer le meilleur score
        scores = [attempt.score for attempt in attempts if attempt.score is not None]
        best_score = max(scores) if scores else 0
        
        # Déterminer le statut
        if best_score >= 70:
            status = 'completed'
        elif best_score > 0:
            status = 'in_progress'
        else:
            status = 'not_started'
            
        return {
            'attempts_count': len(attempts),
            'remaining_attempts': self.max_attempts - len(attempts) if self.max_attempts else None,
            'best_score': best_score,
            'last_attempt': attempts[0],
            'status': status
        }
    
    def get_stats(self, course_id=None):
        """Récupère les statistiques globales de l'exercice."""
        # Filtrer les tentatives par cours si spécifié
        attempts = self.attempts
        if course_id:
            attempts = [a for a in attempts if a.course_id == course_id]
        
        if not attempts:
            return {
                'total_attempts': 0,
                'total_students': 0,
                'average_score': 0,
                'completion_rate': 0,
                'success_rate': 0
            }
        
        # Calculer les statistiques
        total_attempts = len(attempts)
        unique_students = len(set(attempt.student_id for attempt in attempts))
        scores = [attempt.score for attempt in attempts if attempt.score is not None]
        average_score = sum(scores) / len(scores) if scores else 0
        
        # Calculer le taux de complétion (pourcentage d'étudiants ayant fait au moins une tentative)
        students_query = User.query.filter_by(role='student')
        if course_id:
            course = Course.query.get(course_id)
            if course:
                students_query = course.class_obj.students
        total_students = students_query.count()
        completion_rate = (unique_students / total_students * 100) if total_students > 0 else 0
        
        # Calculer le taux de réussite (pourcentage de tentatives avec un score >= 70%)
        successful_attempts = len([score for score in scores if score >= 70])
        success_rate = (successful_attempts / len(scores) * 100) if scores else 0
        
        return {
            'total_attempts': total_attempts,
            'total_students': unique_students,
            'average_score': average_score,
            'completion_rate': completion_rate,
            'success_rate': success_rate
        }

class ExerciseAttempt(db.Model):
    __tablename__ = 'exercise_attempt'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    score = db.Column(db.Float)
    answers = db.Column(db.Text)  # Stocké en JSON
    feedback = db.Column(db.Text)  # Stocké en JSON
    completed = db.Column(db.Boolean, default=True)  # Par défaut True car une tentative est considérée comme complétée
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations avec les paramètres overlaps pour éviter les avertissements
    student_user = db.relationship('User', foreign_keys=[student_id], overlaps="exercise_attempts,student")
    exercise_ref = db.relationship('Exercise', overlaps="attempts,exercise", backref=db.backref('student_attempts', lazy=True, overlaps="exercise,attempts", cascade='all, delete-orphan'))
    course_ref = db.relationship('Course', backref=db.backref('exercise_attempts', lazy=True, cascade='all, delete-orphan'))
    
    def get_answers(self):
        """Récupère les réponses de la tentative."""
        if not self.answers:
            return {}
            
        try:
            answers = json.loads(self.answers)
            # Convertir la liste de réponses en dictionnaire
            return {f'answer_{i}': answer for i, answer in enumerate(answers)}
        except json.JSONDecodeError:
            return {}
    
    def get_feedback(self):
        """Récupères le feedback formaté de la tentative."""
        if not self.feedback:
            return None
            
        try:
            return json.loads(self.feedback)
        except json.JSONDecodeError:
            return {
                'error': 'Format de feedback invalide',
                'raw': self.feedback
            }

class CourseFile(db.Model):
    __tablename__ = 'course_file'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)  # Taille en bytes
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', name='fk_file_course'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
