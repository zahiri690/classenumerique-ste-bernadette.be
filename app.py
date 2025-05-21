from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session, abort, Response
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from models import (
    db, User, Class, Course, Exercise, ExerciseAttempt, CourseFile,
    student_class_association, course_exercise
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime, timedelta
from functools import wraps
import logging
import json
import random
import string
import os
import unicodedata
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired
from modified_submit import init_app as init_exercise_routes

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'  # À changer en production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ajout du filtre shuffle pour Jinja2
@app.template_filter('shuffle')
def shuffle_filter(seq):
    try:
        result = list(seq)
        random.shuffle(result)
        return result
    except:
        return seq

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# S'assurer que le dossier d'upload existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuration de l'extension pour les fichiers
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialisation des extensions
db.init_app(app)
csrf = CSRFProtect()
csrf.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize exercise routes
init_exercise_routes(app)

# Fonctions pour les filtres Jinja2
def enumerate_filter(iterable, start=0):
    return enumerate(iterable, start=start)

def from_json_filter(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value

def tojson_filter(value, indent=None):
    return json.dumps(value, indent=indent, ensure_ascii=False)

def get_file_icon(filename):
    """Retourne l'icône Font Awesome appropriée en fonction de l'extension du fichier"""
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    icon_mapping = {
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word',
        'docx': 'fa-file-word',
        'xls': 'fa-file-excel',
        'xlsx': 'fa-file-excel',
        'ppt': 'fa-file-powerpoint',
        'pptx': 'fa-file-powerpoint',
        'txt': 'fa-file-alt',
        'jpg': 'fa-file-image',
        'jpeg': 'fa-file-image',
        'png': 'fa-file-image',
        'gif': 'fa-file-image',
        'zip': 'fa-file-archive',
        'rar': 'fa-file-archive',
        '7z': 'fa-file-archive',
    }
    
    return icon_mapping.get(extension, 'fa-file')  # fa-file est l'icône par défaut

app.jinja_env.globals.update(get_file_icon=get_file_icon)

# Enregistrement des filtres Jinja2
app.jinja_env.filters['enumerate'] = enumerate_filter
app.jinja_env.filters['from_json'] = from_json_filter
app.jinja_env.filters['tojson'] = tojson_filter

# Décorateurs
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_teacher:
            flash('Accès réservé aux enseignants.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def sanitize_filename(filename):
    # Supprimer les accents
    filename = ''.join(c for c in unicodedata.normalize('NFD', filename)
                      if unicodedata.category(c) != 'Mn')
    # Remplacer les espaces par des underscores
    filename = filename.replace(' ', '_')
    # Garder uniquement les caractères alphanumériques et quelques caractères spéciaux
    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
    return filename

def generate_unique_filename(original_filename):
    # Séparer le nom de fichier et l'extension
    name, ext = os.path.splitext(original_filename)
    # Générer un timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Générer une chaîne aléatoire
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    # Combiner le tout
    return f"{name}_{timestamp}_{random_string}{ext}"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.after_request
def add_csrf_token(response):
    if 'csrf_token' not in request.cookies:
        response.set_cookie('csrf_token', generate_csrf())
    return response

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', request.headers)
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)
    logger.debug('Method: %s', request.method)
    logger.debug('Path: %s', request.path)

# Routes
@app.route('/')
@login_required
def index():
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('view_student_classes'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'error')
            return redirect(url_for('register_teacher'))
        
        # Générer un username à partir de l'email
        username = email.split('@')[0]
        
        user = User(
            username=username,
            name=name,
            email=email,
            role='teacher'
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de l\'inscription.', 'error')
            print(f"Erreur d'inscription : {str(e)}")
    
    return render_template('register_teacher.html')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        app.logger.info("Données du formulaire reçues : %s", request.form)
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        app.logger.info("Valeurs extraites - username: %s, email: %s", username, email)
        
        # Vérifier que tous les champs sont remplis
        if not all([username, email, password, confirm_password]):
            missing_fields = []
            if not username: missing_fields.append('nom d\'utilisateur')
            if not email: missing_fields.append('email')
            if not password: missing_fields.append('mot de passe')
            if not confirm_password: missing_fields.append('confirmation du mot de passe')
            
            flash(f'Les champs suivants sont obligatoires : {", ".join(missing_fields)}.', 'error')
            return redirect(url_for('register_student'))
            
        # Vérifier que les mots de passe correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return redirect(url_for('register_student'))
        
        # Vérifier si l'email est déjà utilisé
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'error')
            return redirect(url_for('register_student'))
            
        # Vérifier si le nom d'utilisateur est déjà utilisé
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà utilisé.', 'error')
            return redirect(url_for('register_student'))
        
        try:
            user = User(
                username=username,
                name=username,  # Utiliser le username comme nom par défaut
                email=email,
                role='student'
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            app.logger.info("Nouvel utilisateur créé avec succès - username: %s, email: %s", username, email)
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error("Erreur lors de la création de l'utilisateur : %s", str(e))
            flash('Erreur lors de l\'inscription.', 'error')
            return redirect(url_for('register_student'))
    
    return render_template('register_student.html')

@app.route('/setup-admin')
def setup_admin():
    # Vérifier si un utilisateur existe déjà
    if User.query.first() is not None:
        flash('Un utilisateur existe déjà', 'warning')
        return redirect(url_for('login'))
    
    # Créer un compte administrateur par défaut
    admin = User(
        username='admin',
        name='Admin',
        email='admin@example.com',
        role='admin'
    )
    admin.set_password('admin')
    
    try:
        db.session.add(admin)
        db.session.commit()
        flash('Compte administrateur créé avec succès. Email: admin@example.com, Mot de passe: admin', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la création du compte administrateur', 'error')
    
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('index'))
    
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_dashboard.html', classes=classes)





@app.route('/add_exercise_to_class/<int:exercise_id>', methods=['GET', 'POST'])
@login_required
def add_exercise_to_class(exercise_id):
    if current_user.role == 'student':
        return redirect(url_for('student_dashboard'))

    exercise = Exercise.query.get_or_404(exercise_id)
    if exercise.teacher_id != current_user.id:
        abort(403)

    # Récupérer les classes de l'enseignant
    classes = Class.query.filter_by(teacher_id=current_user.id).all()

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        course_id = request.form.get('course_id')

        if not class_id or not course_id:
            flash('Veuillez sélectionner une classe et un cours', 'error')
            return redirect(url_for('add_exercise_to_class', exercise_id=exercise_id))

        # Vérifier que la classe et le cours existent et appartiennent à l'enseignant
        class_obj = Class.query.get_or_404(class_id)
        course = Course.query.get_or_404(course_id)

        if class_obj.teacher_id != current_user.id or course.class_obj.id != int(class_id):
            abort(403)

        # Ajouter l'exercice au cours s'il n'y est pas déjà
        if exercise not in course.exercises:
            course.exercises.append(exercise)
            db.session.commit()
            flash('L\'exercice a été ajouté au cours avec succès !', 'success')
        else:
            flash('L\'exercice est déjà dans ce cours', 'warning')

        return redirect(url_for('exercise_library'))

    return render_template('add_exercise_to_class.html', exercise=exercise, classes=classes)

@app.route('/get_courses/<int:class_id>')
@login_required
def get_courses(class_id):
    if current_user.role == 'student':
        return jsonify([]), 403

    # Vérifier que la classe appartient à l'enseignant
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != current_user.id:
        return jsonify([]), 403

    # Récupérer tous les cours de la classe
    courses = Course.query.filter_by(class_id=class_id).all()
    return jsonify([{'id': course.id, 'title': course.title} for course in courses])

@app.route('/class/<int:class_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_class(class_id):
    logger.debug('='*50)
    logger.debug('TENTATIVE DE SUPPRESSION DE CLASSE')
    logger.debug(f'class_id: {class_id}')
    logger.debug(f'user: {current_user.name} (id: {current_user.id})')
    logger.debug(f'headers: {dict(request.headers)}')
    logger.debug(f'form data: {dict(request.form)}')
    
    # Vérification du token CSRF
    if not request.form.get('csrf_token'):
        logger.error("Token CSRF manquant")
        flash('Erreur de sécurité : token CSRF manquant.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    try:
        # Récupération et vérification de la classe
        class_obj = Class.query.get(class_id)
        if not class_obj:
            logger.error(f"Classe {class_id} non trouvée")
            flash('Classe non trouvée.', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        # Vérification des permissions
        if class_obj.teacher_id != current_user.id:
            logger.error(f"L'utilisateur {current_user.name} n'est pas le professeur de la classe {class_obj.name}")
            flash('Vous n\'êtes pas autorisé à supprimer cette classe.', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        try:
            # Supprimer les cours associés
            for course in class_obj.courses:
                db.session.delete(course)
            
            # Supprimer les associations avec les étudiants
            class_obj.students = []
            
            # Sauvegarder le nom pour le message
            class_name = class_obj.name
            
            # Supprimer la classe
            db.session.delete(class_obj)
            db.session.commit()
            
            logger.info(f"Classe {class_name} supprimée avec succès")
            flash(f'La classe {class_name} a été supprimée avec succès !', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur SQL lors de la suppression: {str(e)}")
            flash('Une erreur est survenue lors de la suppression de la classe.', 'error')
            return redirect(url_for('view_class', class_id=class_id))
            
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        flash('Une erreur inattendue est survenue.', 'error')
        
    return redirect(url_for('teacher_dashboard'))

@app.route('/course/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    if not current_user.is_teacher:
        flash('Seuls les enseignants peuvent supprimer des cours.', 'error')
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(course_id)
    class_obj = Class.query.get_or_404(course.class_id)
    
    # Vérifier que l'enseignant est bien le propriétaire de la classe
    if class_obj.teacher_id != current_user.id:
        flash('Vous n\'avez pas la permission de supprimer ce cours.', 'error')
        return redirect(url_for('view_class', class_id=class_obj.id))
    
    try:
        # Supprimer les fichiers physiques
        for course_file in course.course_files:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], course_file.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f"Erreur lors de la suppression du fichier {course_file.filename}: {str(e)}")
        
        # Supprimer le cours (les fichiers et exercices seront supprimés automatiquement grâce à cascade)
        db.session.delete(course)
        db.session.commit()
        flash('Le cours a été supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de la suppression du cours.', 'error')
        app.logger.error(f"Erreur lors de la suppression du cours {course_id}: {str(e)}")
    
    return redirect(url_for('view_class', class_id=class_obj.id))

@app.route('/class/<int:class_id>/remove-student/<int:student_id>', methods=['POST'])
@login_required
def remove_student_from_class(class_id, student_id):
    logger.debug('='*50)
    logger.debug('TENTATIVE DE SUPPRESSION D\'ÉTUDIANT')
    logger.debug(f'class_id: {class_id}')
    logger.debug(f'student_id: {student_id}')
    logger.debug(f'user: {current_user.name} (id: {current_user.id}, is_teacher: {current_user.is_teacher})')
    logger.debug(f'headers: {dict(request.headers)}')
    logger.debug(f'form data: {dict(request.form)}')
    
    # Vérification du token CSRF
    if not request.form.get('csrf_token'):
        logger.error("Token CSRF manquant")
        flash('Erreur de sécurité : token CSRF manquant.', 'error')
        return redirect(url_for('view_class', class_id=class_id))
    
    # Vérification des permissions
    if not current_user.is_teacher:
        logger.error(f"Accès refusé : l'utilisateur {current_user.name} n'est pas un enseignant")
        flash('Accès réservé aux enseignants.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Vérification de la classe
        class_obj = Class.query.get(class_id)
        if not class_obj:
            logger.error(f"Classe {class_id} non trouvée")
            flash('Classe non trouvée.', 'error')
            return redirect(url_for('teacher_dashboard'))
            
        if class_obj.teacher_id != current_user.id:
            logger.error(f"L'utilisateur {current_user.name} n'est pas le professeur de la classe {class_obj.name}")
            flash('Vous n\'êtes pas le professeur de cette classe.', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        # Vérification de l'étudiant
        student = User.query.get(student_id)
        if not student:
            logger.error(f"Étudiant {student_id} non trouvé")
            flash('Étudiant non trouvé.', 'error')
            return redirect(url_for('view_class', class_id=class_id))
            
        if not student in class_obj.students:
            logger.error(f"L'étudiant {student.name} n'est pas dans la classe {class_obj.name}")
            flash('Cet étudiant n\'est pas inscrit dans cette classe.', 'error')
            return redirect(url_for('view_class', class_id=class_id))
        
        try:
            # Supprimer l'étudiant de la classe
            class_obj.students.remove(student)
            db.session.commit()
            logger.info(f"Étudiant {student.name} supprimé avec succès de la classe {class_obj.name}")
            flash(f'L\'étudiant {student.name} a été retiré de la classe avec succès.', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur SQL lors de la suppression: {str(e)}")
            flash('Une erreur est survenue lors de la suppression de l\'étudiant.', 'error')
            
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        flash('Une erreur inattendue est survenue.', 'error')
        
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/exercise-library')
@login_required
@teacher_required
def exercise_library():
    # Récupérer les paramètres de filtrage
    search_query = request.args.get('search', '')
    exercise_type = request.args.get('type', '')
    subject = request.args.get('subject', '')
    level = request.args.get('level', '')

    # Construire la requête de base
    query = Exercise.query

    # Appliquer les filtres
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Exercise.title.ilike(search),
                Exercise.description.ilike(search)
            )
        )
    
    if exercise_type:
        query = query.filter(Exercise.exercise_type == exercise_type)
    
    # Exécuter la requête
    exercises = query.all()

    # Debug: afficher le nombre d'exercices trouvés
    app.logger.info(f"Nombre d'exercices trouvés : {len(exercises)}")
    for ex in exercises:
        app.logger.info(f"Exercice : {ex.title} (type: {ex.exercise_type})")

    return render_template('exercise_library.html',
                         exercises=exercises,
                         exercise_types=Exercise.EXERCISE_TYPES,
                         search_query=search_query,
                         selected_type=exercise_type,
                         selected_subject=subject,
                         selected_level=level)

@app.route('/exercise/<int:exercise_id>')
@login_required
def view_exercise(exercise_id):
    try:
        app.logger.info(f'Accessing exercise {exercise_id}')
        exercise = Exercise.query.get_or_404(exercise_id)
        app.logger.info(f'Found exercise: {exercise.title}')
        course_id = request.args.get('course_id', type=int)
        course = Course.query.get(course_id) if course_id else None
        app.logger.info(f'Course ID: {course_id}, Course: {course.title if course else None}')
    except Exception as e:
        app.logger.error(f'Error accessing exercise: {str(e)}')
        app.logger.exception('Full error:')
        return 'Une erreur est survenue lors de l\'accès à l\'exercice.', 500
    
    # Si l'exercice est accédé via un cours, vérifier que l'étudiant est inscrit
    if course and current_user.role == 'student':
        class_obj = Class.query.get(course.class_id)
        if not class_obj or current_user not in class_obj.students:
            flash('Vous n\'avez pas accès à cet exercice.', 'error')
            return redirect(url_for('index'))
    
    attempt = None
    content = None
    progress = None
    
    # Récupérer le contenu de l'exercice
    try:
        content = exercise.get_content()
    except json.JSONDecodeError as e:
        app.logger.error(f'Error decoding exercise content: {str(e)}')
        content = {}
    
    # Si l'utilisateur est un étudiant
    if current_user.role == 'student':
        # Récupérer la dernière tentative
        attempt = ExerciseAttempt.query.filter_by(
            exercise_id=exercise_id,
            student_id=current_user.id
        ).order_by(ExerciseAttempt.created_at.desc()).first()
    
    # Les enseignants peuvent accéder directement aux exercices
    elif current_user.role != 'teacher':
        flash("Vous n'avez pas les permissions nécessaires.", "error")
        return redirect(url_for('index'))
        
    # Récupérer les statistiques et le contenu de l'exercice
    app.logger.info(f'Exercise type: {exercise.exercise_type}')
    app.logger.info(f'Raw content: {exercise.content}')
    try:
        content = exercise.get_content()
        app.logger.info(f'Parsed content: {content}')
        # Mélange des éléments de droite pour les appariements
        if exercise.exercise_type == 'pairs' and 'right_items' in content:
            right_items = content.get('right_items', [])
            shuffled = list(enumerate(right_items))
            import random
            random.shuffle(shuffled)
            content['shuffled_right_items'] = [item for idx, item in shuffled]
            content['shuffled_indices'] = [idx for idx, item in shuffled]
    except Exception as e:
        app.logger.error(f'Error parsing content: {str(e)}')
        app.logger.exception('Full error:')
        content = {'questions': []}
    progress = None
    
    progress = exercise.get_student_progress(current_user.id)
    
    # Choisir le template en fonction du type d'exercice
    template = f'exercise_types/{exercise.exercise_type}.html'
    app.logger.info(f'Using template: {template}')
    
    try:
        # Vérifier que le template existe
        if not os.path.exists(os.path.join(app.template_folder, template)):
            app.logger.error(f'Template not found: {template}')
            return 'Le template pour ce type d\'exercice n\'existe pas.', 500
        
        # Vérifier que les variables sont correctes
        app.logger.info(f'Variables for template:')
        app.logger.info(f'- exercise: {exercise}')
        app.logger.info(f'- attempt: {attempt}')
        app.logger.info(f'- content: {content}')
        app.logger.info(f'- progress: {progress}')
        app.logger.info(f'- course: {course}')
        
        return render_template(template,
                            exercise=exercise,
                            attempt=attempt,
                            content=content,
                            progress=progress,
                            course=course)
    except Exception as e:
        app.logger.error(f'Error rendering template: {str(e)}')
        app.logger.exception('Full template error:')
        return 'Une erreur est survenue lors de l\'affichage de l\'exercice.', 500

@app.route('/exercise/<int:exercise_id>/teacher')
@login_required
def view_exercise_teacher(exercise_id):
    if not current_user.is_teacher:
        flash("Accès non autorisé.", "error")
        return redirect(url_for('index'))
        
    exercise = Exercise.query.get_or_404(exercise_id)
    return render_template('view_exercise_teacher.html', exercise=exercise)


@app.route('/exercise/<int:exercise_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Vérifier que l'utilisateur est l'enseignant qui a créé l'exercice
    if not current_user.is_teacher or (current_user.id != exercise.teacher_id):
        flash('Vous n\'avez pas la permission de modifier cet exercice.', 'error')
        return redirect(url_for('exercise_library'))
    
    if request.method == 'POST':
        exercise.title = request.form.get('title')
        exercise.description = request.form.get('description')

        # Gérer le contenu en fonction du type d'exercice
        content = {}
        if exercise.exercise_type == 'fill_in_blanks':
            sentences = request.form.getlist('sentences[]')
            words = request.form.getlist('words[]')
            answers = request.form.getlist('answers[]')
            content = {
                'sentences': sentences,
                'words': words,
                'answers': answers
            }
        elif exercise.exercise_type == 'qcm':
            questions = []
            question_texts = request.form.getlist('questions[]')
            options = request.form.getlist('options[]')
            correct_answers = request.form.getlist('correct[]')

            # Regrouper les options par question
            options_per_question = []
            current_options = []

            for option in options:
                if option.strip():
                    current_options.append(option)
                else:
                    if current_options:
                        options_per_question.append(current_options)
                        current_options = []

            if current_options:
                options_per_question.append(current_options)

            # Créer les questions
            for i, question_text in enumerate(question_texts):
                if question_text.strip():
                    options = options_per_question[i] if i < len(options_per_question) else []
                    correct = int(correct_answers[i]) if i < len(correct_answers) else 0

                    question = {
                        'question': question_text,
                        'options': options,
                        'correct': correct
                    }
                    questions.append(question)

            content = {'questions': questions}
        elif exercise.exercise_type == 'underline_words':
            sentences = request.form.getlist('sentences[]')
            words_to_underline = request.form.getlist('words_to_underline[]')

            content = {
                'sentences': []
            }

            for i, sentence in enumerate(sentences):
                words = sentence.strip().split()
                underline_words = [w.strip() for w in words_to_underline[i].split(',')]

                content['sentences'].append({
                    'words': words,
                    'words_to_underline': underline_words
                })
        elif exercise.exercise_type == 'pairs':
            pairs = []
            question_count = int(request.form.get('question_count', 0))

            for i in range(question_count):
                pair = {
                    'first': request.form.get(f'pair_{i}_first'),
                    'second': request.form.get(f'pair_{i}_second')
                }
                if pair['first'] and pair['second']:
                    pairs.append(pair)

            content = {'pairs': pairs}
        elif exercise.exercise_type == 'drag_and_drop':
            items = request.form.getlist('items[]')
            zones = request.form.getlist('zones[]')
            if len(items) != len(zones):
                flash('Le nombre d\'éléments et de zones doit être identique.', 'error')
                return redirect(url_for('edit_exercise', exercise_id=exercise_id))

            content = {
                'items': [{'text': item, 'zone': zone} for item, zone in zip(items, zones)]
            }
        elif exercise.exercise_type == 'file':
            instructions = request.form.get('instructions', '').strip()
            if not instructions:
                flash('Les instructions sont requises pour un exercice de dépôt de fichier.', 'error')
                return redirect(url_for('edit_exercise', exercise_id=exercise_id))

            content = {'instructions': instructions}

        # Sauvegarder le contenu
        exercise.set_content(content)
        db.session.commit()

        flash('Exercice modifié avec succès !', 'success')
        return redirect(url_for('view_exercise', exercise_id=exercise.id))

    # Récupérer le nombre de tentatives pour cet exercice
    from models import ExerciseAttempt
    attempts_count = ExerciseAttempt.query.filter_by(exercise_id=exercise.id).count()

    return render_template(
        f'exercise_types/{exercise.exercise_type}_edit.html',
        exercise=exercise,
        content=exercise.get_content(),
        attempts_count=attempts_count
    )

@app.route('/course/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Vérifier que l'utilisateur a accès au cours
    if not current_user.is_teacher and not current_user.is_enrolled(course.class_obj.id):
        flash('Vous n\'avez pas accès à ce cours.', 'error')
        return redirect(url_for('index'))

    # Si c'est un enseignant, récupérer la liste des exercices disponibles
    exercises_available = []
    if current_user.is_teacher:
        # Récupérer tous les exercices créés par l'enseignant qui ne sont pas déjà dans le cours
        exercises_available = Exercise.query.filter_by(teacher_id=current_user.id).filter(
            ~Exercise.id.in_([ex.id for ex in course.exercises])
        ).all()

    # Récupérer les exercices du cours
    exercises = course.exercises

    # Pour les enseignants, récupérer les statistiques du cours
    stats = None
    if current_user.is_teacher:
        stats = {
            'total_students': len(course.class_obj.students),
            'total_exercises': len(exercises),
            'exercises_stats': []
        }


        for exercise in exercises:
            exercise_stats = {
                'title': exercise.title,
                'completion_rate': 0,
                'average_score': 0,
                'needs_grading': 0
            }

            total_students = len(course.class_obj.students)
            if total_students > 0:
                completed = 0
                total_score = 0
                needs_grading = 0

                for student in course.class_obj.students:
                    progress = exercise.get_student_progress(student.id)
                    if progress and progress.get('best_score') is not None:
                        completed += 1
                        total_score += progress['best_score']
                    elif progress and progress.get('needs_grading'):
                        needs_grading += 1

                exercise_stats['completion_rate'] = (completed / total_students) * 100
                if completed > 0:
                    exercise_stats['average_score'] = total_score / completed
                exercise_stats['needs_grading'] = needs_grading

            stats['exercises_stats'].append(exercise_stats)

    # Calcul de la progression pour les étudiants (partie droite)
    progress_records = []
    total_exercises = len(exercises)
    if not current_user.is_teacher:
        for ex in exercises:
            progress = ex.get_student_progress(current_user.id)
            if progress and progress.get('best_score', 0) >= 70:
                progress_records.append({'exercise_id': ex.id, 'student_id': current_user.id})

    return render_template('view_course.html',
                         course=course,
                         exercises=exercises,
                         exercises_available=exercises_available,
                         stats=stats,
                         progress_records=progress_records,
                         total_exercises=total_exercises)

@app.route('/class/<int:class_id>/create_course', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course(class_id):
    class_obj = Class.query.get_or_404(class_id)

    # Vérifier que l'utilisateur est bien le professeur de cette classe
    if class_obj.teacher_id != current_user.id:
        flash("Vous n'avez pas l'autorisation de créer un cours dans cette classe.", 'error')
        return redirect(url_for('teacher_dashboard'))

    class CourseForm(FlaskForm):
        title = StringField('Titre', validators=[DataRequired()])
        content = TextAreaField('Contenu')
        files = MultipleFileField('Fichiers joints')

    form = CourseForm()

    if form.validate_on_submit():
        # Récupérer le contenu de l'éditeur
        content = request.form.get('content', '{}')

        course = Course(
            title=form.title.data,
            content=json.dumps(content),  # Convertir en JSON
            class_id=class_id
        )

        # Gérer les fichiers
        files = request.files.getlist('files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                course_file = CourseFile(
                    filename=filename,
                    original_filename=file.filename,
                    file_type=file.content_type,
                    file_size=os.path.getsize(filepath),
                    course=course
                )
                db.session.add(course_file)

        db.session.add(course)
        db.session.commit()
        flash('Le cours a été créé avec succès.', 'success')
        return redirect(url_for('view_class', class_id=class_id))

    return render_template('create_course.html', form=form, class_id=class_id)

@app.route('/student/classes')
@login_required
def view_student_classes():
    if current_user.is_teacher:
        flash('Cette page est réservée aux étudiants.', 'error')
        return redirect(url_for('teacher_dashboard'))

    enrolled_classes = current_user.classes_enrolled
    return render_template('student_classes.html', classes=enrolled_classes)

@app.route('/class/join_by_code', methods=['GET', 'POST'])
@login_required
def join_class_by_code():
    if request.method == 'POST':
        class_code = request.form.get('class_code')
        if not class_code:
            flash('Le code d\'accès est requis.', 'error')
            return redirect(url_for('view_student_classes'))

        class_obj = Class.query.filter_by(access_code=class_code).first()
        if not class_obj:
            flash('Code d\'accès invalide.', 'error')
            return redirect(url_for('view_student_classes'))

        if current_user in class_obj.students:
            flash('Vous êtes déjà inscrit dans cette classe.', 'warning')
            return redirect(url_for('view_class', class_id=class_obj.id))

        try:
            class_obj.students.append(current_user)
            db.session.commit()
            flash('Vous avez rejoint la classe avec succès !', 'success')
            return redirect(url_for('view_class', class_id=class_obj.id))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'inscription à la classe.', 'error')
            return redirect(url_for('view_student_classes'))

    return redirect(url_for('view_student_classes'))

@app.route('/class/<int:class_id>/view')
@login_required
def view_class(class_id):
    class_obj = Class.query.get_or_404(class_id)

    # Si c'est l'enseignant de la classe
    if current_user.is_teacher and class_obj.teacher_id == current_user.id:
        return view_class_teacher(class_id)

    # Si c'est un étudiant inscrit dans la classe
    if not current_user.is_teacher and class_obj in current_user.classes_enrolled:
        return render_template('view_class.html', class_obj=class_obj)

    flash('Accès non autorisé.', 'error')
    return redirect(url_for('index'))

@app.route('/class/<int:class_id>/view/teacher')
@login_required
@teacher_required
def view_class_teacher(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != current_user.id:
        flash('Vous n\'êtes pas le professeur de cette classe.', 'error')
        return redirect(url_for('index'))
    return render_template('view_class.html', class_obj=class_obj)

@app.route('/course/<int:course_id>/add-exercise', methods=['POST'])
@login_required
def add_exercise_to_course(course_id):
    app.logger.info(f"[add_exercise_to_course] Début de l'ajout d'exercice au cours {course_id}")
    app.logger.info(f"[add_exercise_to_course] Utilisateur: {current_user.id} ({current_user.role})")

    if not current_user.is_teacher:
        app.logger.warning("[add_exercise_to_course] Tentative d'accès non autorisé")
        flash('Accès non autorisé. Seuls les enseignants peuvent ajouter des exercices.', 'error')
        return redirect(url_for('index'))

    course = Course.query.get_or_404(course_id)
    app.logger.info(f"[add_exercise_to_course] Cours trouvé: {course.title}")

    # Vérifier que l'utilisateur est le propriétaire de la classe
    if course.class_obj.teacher_id != current_user.id:
        app.logger.warning("[add_exercise_to_course] L'utilisateur n'est pas le propriétaire de la classe")
        flash('Vous ne pouvez pas modifier ce cours.', 'error')
        return redirect(url_for('index'))

    exercise_id = request.form.get('exercise_id')
    app.logger.info(f"[add_exercise_to_course] ID de l'exercice reçu: {exercise_id}")

    if not exercise_id:
        app.logger.warning("[add_exercise_to_course] Aucun exercice sélectionné")
        flash('Veuillez sélectionner un exercice.', 'error')
        return redirect(url_for('view_course', course_id=course_id))

    exercise = Exercise.query.get_or_404(exercise_id)
    app.logger.info(f"[add_exercise_to_course] Exercice trouvé: {exercise.title}")

    # Vérifier que l'exercice n'est pas déjà dans le cours
    if exercise in course.exercises:
        app.logger.warning("[add_exercise_to_course] L'exercice est déjà dans le cours")
        flash('Cet exercice est déjà dans le cours.', 'error')
        return redirect(url_for('view_course', course_id=course_id))

    try:
        app.logger.info(f"[add_exercise_to_course] Tentative d'ajout de l'exercice {exercise_id} au cours {course_id}")
        app.logger.info(f"[add_exercise_to_course] État actuel du cours - Exercices: {[ex.id for ex in course.exercises]}")

        course.exercises.append(exercise)
        db.session.commit()

        app.logger.info(f"[add_exercise_to_course] Nouvel état du cours - Exercices: {[ex.id for ex in course.exercises]}")
        flash('Exercice ajouté au cours avec succès !', 'success')
        return redirect(url_for('view_course', course_id=course_id))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"[add_exercise_to_course] Erreur lors de l'ajout : {str(e)}")
        app.logger.error(f"[add_exercise_to_course] Type d'erreur : {type(e).__name__}")
        import traceback
        app.logger.error(f"[add_exercise_to_course] Traceback : {traceback.format_exc()}")
        flash('Erreur lors de l\'ajout de l\'exercice au cours.', 'error')
        return redirect(url_for('view_course', course_id=course_id))

@app.route('/course/<int:course_id>/remove-exercise/<int:exercise_id>', methods=['POST'])
@login_required
def remove_exercise_from_course(course_id, exercise_id):
    if not current_user.is_teacher:
        flash('Accès non autorisé. Seuls les enseignants peuvent retirer des exercices.', 'error')
        return redirect(url_for('index'))

    course = Course.query.get_or_404(course_id)

    # Vérifier que l'utilisateur est le propriétaire de la classe
    if course.class_obj.teacher_id != current_user.id:
        flash('Vous ne pouvez pas modifier ce cours.', 'error')
        return redirect(url_for('index'))

    exercise = Exercise.query.get_or_404(exercise_id)

    try:
        course.exercises.remove(exercise)
        db.session.commit()
        flash('Exercice retiré du cours avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors du retrait de l\'exercice du cours.', 'error')
        print(f"Erreur : {str(e)}")

    return redirect(url_for('view_course', course_id=course_id))

@app.route('/quick-add-exercise/<int:exercise_id>', methods=['GET', 'POST'])
@login_required
def process_quick_add_exercise(exercise_id):
    try:
        # Récupérer l'exercice
        exercise = Exercise.query.get_or_404(exercise_id)
        app.logger.info(f"[quick_add_exercise] Exercice trouvé: {exercise.title}")

        # Récupérer toutes les classes de l'utilisateur
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        app.logger.info(f"[quick_add_exercise] Nombre de classes trouvées: {len(classes)}")

        # Récupérer la classe sélectionnée si elle existe
        selected_class_id = request.args.get('class_id')
        selected_courses = []
        if selected_class_id:
            try:
                # Vérifier que la classe appartient à l'utilisateur
                class_obj = Class.query.get(int(selected_class_id))
                if class_obj and class_obj.teacher_id == current_user.id:
                    selected_courses = Course.query.filter_by(class_id=int(selected_class_id)).all()
                    app.logger.info(f"[quick_add_exercise] Cours trouvés pour la classe {selected_class_id}: {len(selected_courses)}")
            except ValueError:
                app.logger.error(f"[quick_add_exercise] ID de classe invalide: {selected_class_id}")
                selected_courses = []

        # Si c'est une requête POST, traiter l'ajout de l'exercice
        if request.method == 'POST':
            class_id = request.form.get('class_id')
            course_id = request.form.get('course_id')

            app.logger.info(f"[process_quick_add_exercise] Données reçues - class_id: {class_id}, course_id: {course_id}")

            if not class_id or not course_id:
                flash('Veuillez sélectionner une classe et un cours.', 'error')
                return redirect(url_for('process_quick_add_exercise', exercise_id=exercise_id, class_id=class_id))

            # Vérifier que la classe appartient à l'utilisateur
            class_obj = Class.query.get(class_id)
            if not class_obj or class_obj.teacher_id != current_user.id:
                flash('Classe non trouvée ou accès non autorisé.', 'error')
                return redirect(url_for('exercise_library'))

            # Vérifier que le cours appartient à la classe
            course = Course.query.get(course_id)
            if not course or course.class_id != int(class_id):
                flash('Cours non trouvé ou accès non autorisé.', 'error')
                return redirect(url_for('exercise_library'))

            # Ajouter l'exercice au cours s'il n'y est pas déjà
            if exercise not in course.exercises:
                app.logger.info(f"[process_quick_add_exercise] Ajout de l'exercice {exercise_id} au cours {course_id}")
                course.exercises.append(exercise)
                db.session.commit()
                flash('Exercice ajouté avec succès au cours !', 'success')
                return redirect(url_for('view_course', course_id=course_id))
            else:
                app.logger.info(f"[process_quick_add_exercise] L'exercice {exercise_id} est déjà dans le cours {course_id}")
                flash('Cet exercice est déjà dans le cours.', 'info')
                return redirect(url_for('view_course', course_id=course_id))

        # Pour les requêtes GET, afficher le formulaire
        return render_template('add_exercise_to_class.html',
                             exercise=exercise,
                             classes=classes,
                             selected_class_id=selected_class_id,
                             selected_courses=selected_courses)

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"[process_quick_add_exercise] Erreur lors de l'ajout de l'exercice: {str(e)}")
        app.logger.error(f"[process_quick_add_exercise] Type d'erreur: {type(e).__name__}")
        import traceback
        app.logger.error(f"[process_quick_add_exercise] Traceback: {traceback.format_exc()}")
        flash('Une erreur est survenue lors de l\'ajout de l\'exercice.', 'error')
        return redirect(url_for('process_quick_add_exercise', exercise_id=exercise_id))

@app.route('/class/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash('Le nom de la classe est requis.', 'error')
            return redirect(url_for('create_class'))

        # Générer un code d'accès unique
        import random
        import string

        access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while Class.query.filter_by(access_code=access_code).first() is not None:
            access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        try:
            new_class = Class(
                name=name,
                description=description,
                teacher_id=current_user.id,
                access_code=access_code
            )

            db.session.add(new_class)
            db.session.commit()

            # Afficher le code d'accès à l'enseignant
            flash(f'Classe créée avec succès ! Code d\'accès : {access_code}', 'success')
            return redirect(url_for('view_class', class_id=new_class.id))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de la création de la classe.', 'error')
            return redirect(url_for('create_class'))

    return render_template('create_class.html')

@app.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    class_obj = Class.query.get_or_404(class_id)

    # Vérifier que l'utilisateur est bien le propriétaire de la classe
    if class_obj.teacher_id != current_user.id:
        flash('Vous n\'avez pas la permission de modifier cette classe.', 'error')
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash('Le nom de la classe est requis.', 'error')
            return redirect(url_for('edit_class', class_id=class_id))
    class_obj = Class.query.get_or_404(class_id)

    # Vérifier que l'utilisateur est bien le propriétaire de la classe
    if class_obj.teacher_id != current_user.id:
        flash('Vous n\'avez pas la permission de modifier cette classe.', 'error')
        return redirect(url_for('teacher_dashboard'))

    email = request.form.get('email')
    if not email:
        flash('L\'email de l\'étudiant est requis.', 'error')
        return redirect(url_for('view_class', class_id=class_id))

    student = User.query.filter_by(email=email).first()
    if not student:
        flash('Aucun étudiant trouvé avec cet email.', 'error')
        return redirect(url_for('view_class', class_id=class_id))

    if student in class_obj.students:
        flash('Cet étudiant est déjà inscrit dans cette classe.', 'warning')
        return redirect(url_for('view_class', class_id=class_id))

    try:
        class_obj.students.append(student)
        db.session.commit()
        flash('Étudiant ajouté avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de l\'ajout de l\'étudiant.', 'error')

    return redirect(url_for('view_class', class_id=class_id))

@app.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    class_obj = Class.query.get_or_404(course.class_id)

    # Vérifier que l'utilisateur est le professeur de la classe
    if current_user.id != class_obj.teacher_id:
        flash("Vous n'êtes pas autorisé à modifier ce cours.", 'error')
        return redirect(url_for('view_class', class_id=class_obj.id))

    class CourseForm(FlaskForm):
        title = StringField('Titre', validators=[DataRequired()])
        files = MultipleFileField('Ajouter des fichiers')

    form = CourseForm(obj=course)

    if form.validate_on_submit():
        course.title = form.title.data
        course.content = json.dumps(request.form.get('content', '{}'))  # Convertir en JSON

        # Gérer les nouveaux fichiers
        files = request.files.getlist('files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                course_file = CourseFile(
                    filename=filename,
                    original_filename=file.filename,
                    file_type=file.content_type,
                    file_size=os.path.getsize(filepath),
                    course=course
                )
                db.session.add(course_file)

        db.session.commit()
        flash('Le cours a été modifié avec succès !', 'success')
        return redirect(url_for('view_course', course_id=course.id))

    return render_template('edit_course.html', course=course, form=form)

@app.route('/course/<int:course_id>/file/<int:file_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_course_file(course_id, file_id):
    course = Course.query.get_or_404(course_id)
    course_file = CourseFile.query.get_or_404(file_id)

    # Vérifier que le fichier appartient bien au cours
    if course_file.course_id != course.id:
        return jsonify({'error': 'Ce fichier n\'appartient pas à ce cours.'}), 403

    # Vérifier que l'utilisateur est bien le professeur de la classe
    class_obj = Class.query.get(course.class_id)
    if current_user.id != class_obj.teacher_id:
        return jsonify({'error': 'Vous n\'êtes pas autorisé à supprimer ce fichier.'}), 403

    try:
        # Supprimer le fichier physique
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], course_file.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        # Supprimer l'entrée dans la base de données
        db.session.delete(course_file)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/exercise/underline-words-example')
def underline_words_example():
    return render_template('exercise_types/underline_words_example.html')



class ExerciseForm(FlaskForm):
    exercise_type = SelectField('Type d\'exercice', choices=[
        ('qcm', 'QCM'),
        ('word_search', 'Mots mêlés'),
        ('fill_in_blanks', 'Texte à trous'),
        ('pairs', 'Association de paires')
    ], validators=[DataRequired()])
    title = StringField('Titre', validators=[DataRequired()])
    description = TextAreaField('Description')

@app.route('/exercise/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_exercise():
    form = ExerciseForm()
    
    if form.validate_on_submit():
        # Récupérer les données du formulaire
        title = form.title.data
        description = form.description.data
        exercise_type = form.exercise_type.data
        content = {}

        if exercise_type == 'qcm':
            questions = request.form.getlist('questions[]')
            options = []
            correct_answers = []
            
            for i in range(len(questions)):
                question_options = request.form.getlist(f'options[{i}][]')
                correct_answer = request.form.get(f'correct_answers[{i}]')
                if correct_answer is not None:
                    correct_answer = int(correct_answer)
                options.append(question_options)
                correct_answers.append(correct_answer)

            # Construire la liste des questions avec leurs options et réponses
            questions = []
            for i in range(len(request.form.getlist('questions[]'))):
                question_text = request.form.getlist('questions[]')[i]
                question_options = request.form.getlist(f'options[{i}][]')
                correct_answer = int(request.form.get(f'correct_answers[{i}]', 0))
                
                questions.append({
                    'text': question_text,
                    'options': question_options,
                    'correct_answer': correct_answer
                })
            
            content = {
                'questions': questions
            }

        elif exercise_type == 'fill_in_blanks':
            sentences = request.form.getlist('sentences[]')
            phrases = []
            
            for sentence in sentences:
                # Extraire le mot entre crochets
                import re
                match = re.search(r'\[([^\]]+)\]', sentence)
                if match:
                    answer = match.group(1)
                    text = re.sub(r'\[([^\]]+)\]', '___', sentence)
                    phrases.append({
                        'text': text,
                        'answer': answer
                    })
            
            content = {
                'phrases': phrases
            }

        # Créer l'exercice
        # Convertir le contenu en JSON
        content_json = json.dumps(content)
        
        exercise = Exercise(
            title=title,
            description=description,
            exercise_type=exercise_type,
            content=content_json,
            teacher_id=current_user.id
        )

        db.session.add(exercise)
        db.session.commit()

        flash('Exercice créé avec succès !', 'success')
        return redirect(url_for('exercise.exercise_library'))

    return render_template('create_exercise.html', form=form)


    
    if request.method == 'POST':
        try:
            print('Données reçues:', request.form)
            title = request.form.get('exercise_title')
            description = request.form.get('exercise_description', '')
            exercise_type = request.form.get('exercise_type')
            max_attempts = request.form.get('max_attempts', type=int, default=3)

            print('Titre:', title)
            print('Type:', exercise_type)
            print('Tentatives:', max_attempts)

            if not all([title, exercise_type]):
                flash('Le titre et le type d\'exercice sont obligatoires.', 'error')
                return redirect(request.url)

            if max_attempts < 1:
                flash('Le nombre de tentatives doit être au moins égal à 1.', 'error')
                return redirect(request.url)

            # Initialiser le contenu
            content = {}
            
            if exercise_type == 'qcm':
                # Récupérer les questions et leurs options
                questions_data = []
                question_index = 0
                
                while f'question_{question_index}' in request.form:
                    question_text = request.form.get(f'question_{question_index}')
                    options = request.form.getlist(f'options_{question_index}[]')
                    correct_answer = request.form.get(f'correct_{question_index}')
                    
                    app.logger.debug(f'Question {question_index}:')
                    app.logger.debug(f'- Texte: {question_text}')
                    app.logger.debug(f'- Options: {options}')
                    app.logger.debug(f'- Réponse correcte: {correct_answer}')
                    
                    if question_text and options:
                        try:
                            correct_index = int(correct_answer) if correct_answer else None
                            if correct_index is not None and 0 <= correct_index < len(options):
                                questions_data.append({
                                    'question': question_text,
                                    'options': options,
                                    'correct': correct_index
                                })
                            else:
                                flash(f'Index de réponse correcte invalide pour la question {question_index + 1}', 'error')
                                return redirect(request.url)
                        except ValueError:
                            flash(f'Format de réponse invalide pour la question {question_index + 1}', 'error')
                            return redirect(request.url)
                    
                    question_index += 1
                
                if not questions_data:
                    flash('Veuillez ajouter au moins une question avec des options.', 'error')
                    return redirect(request.url)
                
                content = {'questions': questions_data}
            
            elif exercise_type == 'fill_in_blanks':
                # Récupérer les phrases et réponses avec les indices
                sentences = []
                answers = []
                i = 0
                while f'sentence_{i}' in request.form and f'answer_{i}' in request.form:
                    sentence = request.form.get(f'sentence_{i}', '').strip()
                    answer = request.form.get(f'answer_{i}', '').strip()
                    if sentence and answer:
                        sentences.append(sentence)
                        answers.append(answer)
                    i += 1
                
                print('Données du formulaire:', dict(request.form))
                print('Phrases après nettoyage:', sentences)
                print('Réponses après nettoyage:', answers)
                
                if not sentences:
                    flash('Veuillez ajouter au moins une phrase.', 'error')
                    return redirect(request.url)
                    
                if not answers:
                    flash('Veuillez ajouter au moins une réponse.', 'error')
                    return redirect(request.url)
                    
                if len(sentences) != len(answers):
                    flash('Le nombre de phrases et de réponses ne correspond pas.', 'error')
                    return redirect(request.url)
                
                content = {
                    'sentences': [
                        {'text': sentence, 'answer': answer} for sentence, answer in zip(sentences, answers)
                    ]
                }

            elif exercise_type == 'word_search':
                # Récupérer les mots et la taille de la grille
                words = request.form.getlist('words[]')
                grid_width = request.form.get('grid_width', type=int)
                grid_height = request.form.get('grid_height', type=int)

                # Validation
                if not words:
                    flash('Veuillez ajouter au moins un mot.', 'error')
                    return redirect(request.url)

                if not grid_width or not grid_height:
                    flash('Veuillez spécifier la taille de la grille.', 'error')
                    return redirect(request.url)

                if not (5 <= grid_width <= 15 and 5 <= grid_height <= 15):
                    flash('La taille de la grille doit être entre 5x5 et 15x15.', 'error')
                    return redirect(request.url)

                # Nettoyer et valider les mots
                cleaned_words = []
                for word in words:
                    word = word.strip().upper()
                    if word:
                        if len(word) > max(grid_width, grid_height):
                            flash(f'Le mot "{word}" est trop long pour la grille.', 'error')
                            return redirect(request.url)
                        if not word.isalpha():
                            flash(f'Le mot "{word}" contient des caractères non autorisés.', 'error')
                            return redirect(request.url)
                        cleaned_words.append(word)

                if not cleaned_words:
                    flash('Veuillez ajouter au moins un mot valide.', 'error')
                    return redirect(request.url)

                content = {
                    'words': cleaned_words,
                    'grid_width': grid_width,
                    'grid_height': grid_height
                }

            elif exercise_type == 'fill_in_blanks':
                content = {
                    'sentences': [
                        {'text': sentence, 'answer': answer}
                        for sentence, answer in zip(sentences, answers)
                    ],
                    'available_words': answers
                }
            elif exercise_type == 'underline_words':
                sentences = request.form.getlist('sentences[]')
                words_to_underline = request.form.getlist('words_to_underline[]')
                
                if not sentences or not words_to_underline:
                    flash('Veuillez ajouter au moins une phrase avec des mots à souligner.', 'error')
                    return redirect(request.url)
                
                content = {
                    'sentences': []
                }
                
                for i, sentence in enumerate(sentences):
                    if not sentence.strip():
                        continue
                        
                    # Séparer les mots à souligner et les nettoyer
                    words = [w.strip() for w in words_to_underline[i].split(',') if w.strip()]
                    
                    if not words:
                        continue
                        
                    content['sentences'].append({
                        'text': sentence,
                        'words_to_underline': words
                    })
                
                if not content['sentences']:
                    flash('Veuillez ajouter au moins une phrase valide avec des mots à souligner.', 'error')
                    return redirect(request.url)



            elif exercise_type == 'word_search':
                words = request.form.get('words', '')
                words_list = [word.strip() for word in words.split(',') if word.strip()]
                if not words_list:
                    flash('Veuillez entrer au moins un mot.', 'error')
                    return redirect(url_for('create_exercise'))
                try:
                    grid, placed_words = generate_word_search_grid(words_list)
                    content = {
                        'grid': grid,
                        'words': placed_words
                    }
                except Exception as e:
                    flash(f'Erreur lors de la génération de la grille : {str(e)}', 'error')
                    return redirect(url_for('create_exercise'))

            elif exercise_type == 'pairs':
                pairs = []
                form_data = request.form.to_dict(flat=False)
                pair_indices = set()
                
                # Trouver tous les indices de paires dans le formulaire
                for key in form_data:
                    if key.startswith('pairs[') and '][first]' in key:
                        index = key[len('pairs['):key.find(']')]
                        pair_indices.add(index)
                
                if not pair_indices:
                    flash('Au moins une paire est requise pour l\'exercice d\'association.', 'error')
                    return redirect(request.url)
                
                # Traiter chaque paire
                for index in sorted(pair_indices):
                    first = request.form.get(f'pairs[{index}][first]')
                    second = request.form.get(f'pairs[{index}][second]')
                    
                    if not all([first, second]):
                        flash(f'La paire {int(index) + 1} est incomplète.', 'error')
                        return redirect(request.url)
                    
                    pairs.append({
                        'first': first,
                        'second': second
                    })
                
                content = {'pairs': pairs}

            elif exercise_type == 'file':
                allowed_extensions = request.form.get('allowed_extensions', '').strip()
                max_size = request.form.get('max_size', '5')
                
                try:
                    max_size = int(max_size)
                    if max_size <= 0:
                        raise ValueError
                except ValueError:
                    flash('La taille maximale doit être un nombre positif.', 'error')
                    return redirect(request.url)
                
                content = {
                    'allowed_extensions': [ext.strip().lower() for ext in allowed_extensions.split(',') if ext.strip()],
                    'max_size': max_size
                }
            
                
                if not content['sentences']:
                    flash('Au moins une phrase avec sa réponse est requise.', 'error')
                    return redirect(request.url)

            # Créer l'exercice
            exercise = Exercise(
                title=title,
                description=description,
                exercise_type=exercise_type,
                content=json.dumps(content),
                max_attempts=max_attempts,
                teacher_id=current_user.id
            )

            db.session.add(exercise)
            db.session.commit()

            flash('Exercice créé avec succès !', 'success')
            return redirect(url_for('exercise_library'))
    
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue : {str(e)}', 'error')
            return redirect(request.url)
    
    # GET request
    return render_template('create_exercise.html', exercise_types=Exercise.EXERCISE_TYPES)

@app.route('/api/class/<int:class_id>/courses')
@login_required
def get_class_courses_api(class_id):
    try:
        app.logger.info(f"[get_class_courses_api] Récupération des cours pour la classe {class_id}")
        
        # Vérifier si l'utilisateur a accès à la classe
        class_obj = Class.query.get_or_404(class_id)
        
        if current_user.is_teacher:
            if class_obj.teacher_id != current_user.id:
                app.logger.warning(f"[get_class_courses_api] L'enseignant {current_user.id} n'a pas accès à la classe {class_id}")
                return jsonify({'error': 'Non autorisé'}), 403
        else:
            if class_obj not in current_user.classes_enrolled:
                app.logger.warning(f"[get_class_courses_api] L'étudiant {current_user.id} n'est pas inscrit à la classe {class_id}")
                return jsonify({'error': 'Non autorisé'}), 403
        
        # Récupérer tous les cours de la classe
        courses = Course.query.filter_by(class_id=class_id).all()
        app.logger.info(f"[get_class_courses_api] {len(courses)} cours trouvés")
        
        # Convertir en format JSON
        courses_data = [{
            'id': course.id,
            'title': course.title
        } for course in courses]
        
        app.logger.info(f"[get_class_courses_api] Données renvoyées: {courses_data}")
        return jsonify(courses_data)
        
    except Exception as e:
        app.logger.error(f"[get_class_courses_api] Erreur API courses: {str(e)}")
        app.logger.error(f"[get_class_courses_api] Type d'erreur: {type(e).__name__}")
        import traceback
        app.logger.error(f"[get_class_courses_api] Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Erreur API courses: {str(e)}'}), 500

@app.route('/exercise/<int:exercise_id>/submit', methods=['POST'])
@login_required
def submit_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    course_id = request.form.get('course_id')
    
    # Si un course_id est fourni, vérifier les permissions
    if course_id:
        course = Course.query.get_or_404(course_id)
        if not current_user.is_enrolled(course.class_obj.id):
            flash('Vous n\'avez pas accès à cet exercice.', 'error')
            return redirect(url_for('student_classes'))
        
        # Vérifier que l'exercice fait partie du cours
        if exercise not in course.exercises:
            flash('Cet exercice ne fait pas partie du cours.', 'error')
            return redirect(url_for('view_course', course_id=course_id))
    
    # Vérifier le nombre de tentatives restantes
    progress = exercise.get_student_progress(current_user.id)
    if exercise.max_attempts and progress and progress['remaining_attempts'] is not None and progress['remaining_attempts'] <= 0:
        flash('Vous avez atteint le nombre maximum de tentatives pour cet exercice.', 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))
        return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))
    
    # Traiter les réponses
    answers = []
    score = 0
    feedback = []
    content = exercise.get_content()
    
    if exercise.exercise_type == 'qcm':
        total_questions = len(content['questions'])
        correct_answers = 0
        
        app.logger.debug(f'Content: {content}')
        for i, question in enumerate(content['questions']):
            answer = request.form.get(f'answer_{i}')
            app.logger.debug(f'Réponse brute pour la question {i}: {answer}')
            
            # Convertir la réponse en entier
            try:
                answer = int(answer) if answer is not None else -1
            except (ValueError, TypeError):
                answer = -1
            answers.append(answer)
            
            # Accepter à la fois 'correct' et 'correct_answer' comme clé de la bonne réponse
            correct_key = 'correct'
            if 'correct' not in question and 'correct_answer' in question:
                correct_key = 'correct_answer'
            if correct_key not in question:
                app.logger.error(f"La question {i} ne contient pas la clé 'correct' ou 'correct_answer'. Structure de la question : {question}")
                feedback.append({
                    'question': i + 1,
                    'correct': False,
                    'message': "Erreur interne : la question est mal structurée. Merci de contacter l'enseignant."
                })
                continue  # On passe à la question suivante
            # S'assurer que la valeur est bien un entier pour la comparaison
            try:
                correct = int(question[correct_key])
            except (ValueError, TypeError, KeyError):
                correct = -1
            app.logger.debug(f'Question {i} - Réponse de l\'utilisateur: {answer}, Réponse correcte: {correct}')
            
            # Forcer la conversion en int pour éviter les erreurs de type
            try:
                answer_int = int(answer)
            except (ValueError, TypeError):
                app.logger.warning(f"Impossible de convertir la réponse utilisateur '{answer}' en int pour la question {i}.")
                answer_int = -999
            try:
                correct_int = int(correct)
            except (ValueError, TypeError):
                app.logger.warning(f"Impossible de convertir la réponse correcte '{correct}' en int pour la question {i}.")
                correct_int = -999
            # Vérifier si la réponse est correcte
            if answer_int == correct_int:
                correct_answers += 1
                app.logger.debug(f'Question {i} - Bonne réponse !')
                feedback.append({
                    'question': i + 1,
                    'correct': True,
                    'message': 'Bonne réponse !'
                })
            else:
                # Récupérer le texte de la réponse correcte
                correct_option = question['options'][correct] if 0 <= correct < len(question['options']) else 'Non spécifiée'
                app.logger.debug(f'Question {i} - Mauvaise réponse. Attendu: {correct_option}')
                feedback.append({
                    'question': i + 1,
                    'correct': False,
                    'message': f'La réponse correcte était : {correct_option}'
                })
        
        app.logger.debug(f'Réponses correctes: {correct_answers}, Total questions: {total_questions}')
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        app.logger.debug(f'Score final: {score}%')
    
    elif exercise.exercise_type == 'fill_in_blanks':
        user_answers = []
        correct_answers = content.get('answers', [])
        i = 0
        while True:
            answer = request.form.get(f'answer_{i}')
            if answer is None:
                break
            user_answers.append(answer.strip())
            i += 1
        
        if len(user_answers) != len(correct_answers):
            flash('Nombre de réponses incorrect.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id))
        
        score = 0
        feedback = []
        for i, (user_ans, correct_ans) in enumerate(zip(user_answers, correct_answers)):
            is_correct = user_ans.strip().lower() == correct_ans.strip().lower()
            score += 1 if is_correct else 0
            feedback.append({
                'user_answer': user_ans,
                'correct_answer': correct_ans,
                'is_correct': is_correct
            })
        
        max_score = len(correct_answers)
        score = (score / max_score) * 100 if max_score > 0 else 0
    
    elif exercise.exercise_type == 'word_search':
        found_words = request.form.getlist('found_words[]')
        total_words = len(content['words'])
        correct_words = 0
        
        # Convertir les mots trouvés et les mots à chercher en minuscules pour la comparaison
        found_words = [word.lower().strip() for word in found_words]
        target_words = [word.lower().strip() for word in content['words']]
        
        for word in found_words:
            if word in target_words:
                correct_words += 1
                feedback.append({
                    'word': word,
                    'correct': True,
                    'message': 'Mot trouvé !'
                })
        
        # Ajouter le feedback pour les mots non trouvés
        for word in target_words:
            if word not in found_words:
                feedback.append({
                    'word': word,
                    'correct': False,
                    'message': 'Mot non trouvé'
                })
        
        score = (correct_words / total_words) * 100 if total_words > 0 else 0
        
    elif exercise.exercise_type == 'pairs':
        # Structure attendue : 'correct_pairs': [[0, 0], [1, 1], ...], left_items, right_items
        correct_pairs = content.get('correct_pairs', [])
        total_pairs = len(correct_pairs)
        correct_count = 0
        user_pairs = []
        for i in range(total_pairs):
            left = request.form.get(f'left_{i}')
            right = request.form.get(f'right_{i}')
            if left is not None and right is not None:
                try:
                    left_idx = int(left)
                    right_idx = int(right)
                    user_pairs.append([left_idx, right_idx])
                    answers.append({'left': left_idx, 'right': right_idx})
                except (ValueError, TypeError):
                    continue
        for pair in correct_pairs:
            if pair in user_pairs:
                correct_count += 1
                feedback.append({'pair': pair, 'correct': True, 'message': 'Paire correcte !'})
            else:
                feedback.append({'pair': pair, 'correct': False, 'message': 'Paire incorrecte'})
        score = (correct_count / total_pairs) * 100 if total_pairs > 0 else 0
    
    # S'assurer que le score est un nombre valide
    if score is None:
        score = 0.0
    
    # Enregistrer la tentative
    attempt = ExerciseAttempt(
        student_id=current_user.id,
        exercise_id=exercise_id,
        course_id=course_id,
        score=float(score),  # Convertir explicitement en float
        answers=json.dumps(answers),
        feedback=json.dumps(feedback),
        completed=True
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    # Rafraîchir l'objet depuis la base de données pour s'assurer que tout est à jour
    db.session.refresh(attempt)
    
    flash(f'Exercice soumis avec succès ! Score : {score:.1f}%', 'success')
    return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))

@app.route('/exercise/<int:exercise_id>/stats')
@login_required
@teacher_required
def exercise_stats(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    course_id = request.args.get('course_id', type=int)
    
    # Vérifier que l'enseignant a le droit d'accéder à ces statistiques
    has_access = False
    
    # Vérifier si l'enseignant est le créateur de l'exercice
    if exercise.teacher_id == current_user.id:
        has_access = True
    else:
        # Vérifier si l'exercice est utilisé dans l'une des classes de l'enseignant
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        for class_obj in teacher_classes:
            for course in class_obj.courses:
                if exercise in course.exercises:
                    has_access = True
                    break
            if has_access:
                break
    
    if not has_access:
        flash("Vous n'avez pas l'autorisation de voir ces statistiques.", "error")
        return redirect(url_for('index'))
    
    # Récupérer les statistiques
    stats = exercise.get_stats(course_id)
    
    # Récupérer les informations du cours si spécifié
    course = Course.query.get(course_id) if course_id else None
    
    # Ajouter les informations de progression pour chaque étudiant
    student_progress = []
    
    if course:
        # Pour un cours spécifique, ne montrer que les étudiants de la classe associée
        students_to_show = course.class_obj.students
    else:
        # Sans cours spécifié, montrer tous les étudiants qui ont déjà fait l'exercice
        attempts = ExerciseAttempt.query.filter_by(exercise_id=exercise.id).distinct(ExerciseAttempt.student_id).all()
        student_ids = [a.student_id for a in attempts]
        students_to_show = User.query.filter(User.id.in_(student_ids), User.role=='student').all()
    
    for student in students_to_show:
        progress = exercise.get_student_progress(student.id)
        if progress:
            student_progress.append({
                'student': student,
                'progress': progress
            })
    
    return render_template('exercise_stats.html',
                         exercise=exercise,
                         course=course,
                         stats=stats,
                         student_progress=student_progress)

@app.route('/exercise/<int:exercise_id>/feedback/<int:attempt_id>')
@login_required
def view_feedback(exercise_id, attempt_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    attempt = ExerciseAttempt.query.get_or_404(attempt_id)
    
    # Vérifier que l'utilisateur a le droit de voir ce feedback
    if not current_user.is_teacher and attempt.student_id != current_user.id:
        flash("Vous n'avez pas l'autorisation de voir cette tentative.", "error")
        return redirect(url_for('index'))

    # Si c'est un enseignant, vérifier qu'il enseigne dans la classe associée au cours
    if current_user.is_teacher and attempt.course_id:
        course = Course.query.get(attempt.course_id)
        if course and course.class_obj.teacher_id != current_user.id:
            flash("Vous n'avez pas l'autorisation de voir cette tentative.", "error")
            return redirect(url_for('index'))
    
    # Convertir les réponses et le feedback en dictionnaires
    answers = {}
    feedback = {}
    
    if exercise.exercise_type == 'qcm':
        answers_list = json.loads(attempt.answers)
        for i, answer in enumerate(answers_list, 1):
            answers[str(i)] = answer
    elif exercise.exercise_type == 'pair_match':
        pairs = json.loads(attempt.answers)
        for i, pair in enumerate(pairs, 1):
            answers[str(i)] = f"{pair['left']} → {pair['right']}"
    
    if attempt.feedback:
        feedback = json.loads(attempt.feedback)
    
    return render_template('feedback.html',
                         exercise=exercise,
                         attempt=attempt,
                         answers=answers,
                         feedback=feedback)

@app.route('/course/<int:course_id>/file/<int:file_id>/download')
@login_required
def download_course_file(course_id, file_id):
    course = Course.query.get_or_404(course_id)
    file = CourseFile.query.get_or_404(file_id)
    
    if file.course_id != course.id:
        flash('Fichier non trouvé.', 'error')
        return redirect(url_for('view_course', course_id=course_id))
    
    # Vérifier que l'utilisateur a accès au cours
    if current_user.is_teacher or any(c.id == course.class_id for c in current_user.classes_enrolled):
        uploads_dir = os.path.join(app.root_path, 'uploads')
        return send_from_directory(uploads_dir, file.filename, as_attachment=True, download_name=file.original_filename)
    else:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('index'))

@app.route('/course/<int:course_id>/get-available-exercises')
@login_required
def get_available_exercises(course_id):
    """Retourne la liste des exercices disponibles pour un cours"""
    if not current_user.is_teacher:
        return jsonify({'error': 'Non autorisé'}), 403
    
    course = Course.query.get_or_404(course_id)
    if course.class_obj.teacher_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    
    # Récupérer tous les exercices disponibles
    exercises = Exercise.query.all()
    
    # Filtrer les exercices qui ne sont pas déjà dans le cours
    available_exercises = [
        {'id': ex.id, 'title': ex.title, 'type': ex.exercise_type}
        for ex in exercises if ex not in course.exercises
    ]
    
    return jsonify(available_exercises)

@app.route('/exercise/<int:exercise_id>/submit/<int:course_id>', methods=['POST'])
@login_required

def submit_answer(exercise_id, course_id=0):
    app.logger.info(f"[DEBUG] submit_exercise_answer called for exercise_id={exercise_id}")
    print("\n=== DÉBUT SUBMIT_ANSWER ===\n")
    print(f"[DEBUG] Soumission pour l'exercice {exercise_id}")
    print(f"[DEBUG] Utilisateur: {current_user.username} (ID: {current_user.id})")
    print("[DEBUG] Form data:", request.form)
    print("[DEBUG] Form data type:", type(request.form))
    
    exercise = Exercise.query.get_or_404(exercise_id)
    # Utiliser le course_id de l'URL ou du formulaire comme fallback
    if not course_id:
        course_id = request.form.get('course_id')
    print(f"[DEBUG] Course ID from route: {course_id}")
    print(f"[DEBUG] Course ID from form: {request.form.get('course_id')}")
    
    if not course_id:
        flash('Erreur: Cours non spécifié', 'error')
        return redirect(url_for('exercise_library'))
    
    # Vérifier que l'étudiant a accès à ce cours
    course = Course.query.get_or_404(course_id)
    if not current_user.is_enrolled(course.class_obj.id):
        flash('Vous n\'avez pas accès à cet exercice.', 'error')
        return redirect(url_for('exercise_library'))
    
    answers = {}
    score = 0
    feedback = []

    if exercise.exercise_type == 'underline_words':
        content = exercise.get_content()
        if not isinstance(content, dict) or 'sentences' not in content:
            flash('Structure de l\'exercice invalide.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))

        total_sentences = len(content['sentences'])
        correct_sentences = 0

        for i, sentence_data in enumerate(content['sentences']):
            student_answers = request.form.getlist(f'underlined_words_{i}[]')
            correct_words = set(word.lower() for word in sentence_data['words_to_underline'])
            student_words = set(word.lower() for word in student_answers)

            is_correct = student_words == correct_words
            if is_correct:
                correct_sentences += 1

            feedback.append({
                'sentence': sentence_data['text'],
                'student_words': list(student_words),
                'correct_words': list(correct_words),
                'is_correct': is_correct
            })

        score = (correct_sentences / total_sentences) * 100 if total_sentences > 0 else 0

    elif exercise.exercise_type == 'pairs':
        content = exercise.get_content()
        if not isinstance(content, dict) or 'pairs' not in content:
            flash('Structure de l\'exercice invalide.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))

        total_pairs = len(content['pairs'])
        correct_pairs = 0

        # Créer un dictionnaire des paires correctes
        correct_matches = {pair['first']: pair['second'] for pair in content['pairs']}

        for first, correct_second in correct_matches.items():
            student_answer = request.form.get(f'pair_{first}')
            is_correct = student_answer == correct_second

            if is_correct:
                correct_pairs += 1

            feedback.append({
                'first': first,
                'student_answer': student_answer,
                'correct_answer': correct_second,
                'is_correct': is_correct
            })

        score = (correct_pairs / total_pairs) * 100 if total_pairs > 0 else 0

    elif exercise.exercise_type == 'fill_in_blanks':
        content = exercise.get_content()
        print("[DEBUG] Contenu de l'exercice:", content)

        # Vérification de la structure attendue
        if not isinstance(content, dict) or 'sentences' not in content or not isinstance(content['sentences'], list):
            app.logger.error(f"[ERREUR STRUCTURE] L'exercice {exercise.id} n'a pas de clé 'sentences' valide dans son contenu: {content}")
            flash("Erreur de configuration de l'exercice : structure des phrases manquante ou invalide.", 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))

        total_questions = len(content['sentences'])
        correct_answers = 0

        for i in range(total_questions):
            student_answer = request.form.get(f'answer_{i}')
            correct_answer = content['sentences'][i]['answer']
            print(f"[DEBUG] Question {i + 1}:")
            print(f"[DEBUG] - Réponse de l'étudiant : {student_answer}")
            print(f"[DEBUG] - Réponse correcte : {correct_answer}")

            if student_answer and student_answer.strip().lower() == correct_answer.strip().lower():
                correct_answers += 1
                feedback.append({
                    'question': content['sentences'][i]['text'],
                    'student_answer': student_answer,
                    'correct_answer': correct_answer,
                    'is_correct': True
                })
            else:
                feedback.append({
                    'question': content['sentences'][i]['text'],
                    'student_answer': student_answer or '',
                    'correct_answer': correct_answer,
                    'is_correct': False
                })

        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
    # Créer une nouvelle tentative
    try:
        # Convertir le score en float pour s'assurer qu'il est bien numérique
        score = float(score)
        app.logger.debug(f'Création de la tentative - Score: {score}')
        
        attempt = ExerciseAttempt(
            student_id=current_user.id,
            exercise_id=exercise_id,
            course_id=course_id,
            score=score,
            answers=json.dumps(answers),
            feedback=json.dumps(feedback)
        )
        
        db.session.add(attempt)
        db.session.commit()
        app.logger.debug('Tentative enregistrée avec succès')
        
        flash(f'Exercice soumis avec succès ! Score : {score:.1f}%', 'success')
        return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))
        
    except Exception as e:
        app.logger.error(f'Erreur lors de la création de la tentative: {str(e)}')
        db.session.rollback()
        flash('Une erreur est survenue lors de l\'enregistrement de votre tentative.', 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id, course_id=course_id))
    return redirect(url_for('view_exercise', exercise_id=exercise_id))

@app.route('/debug/exercises')
@login_required
def debug_exercises():
    if not current_user.is_teacher:
        return "Accès non autorisé", 403
        
    exercises = Exercise.query.all()
    debug_info = []
    
    for ex in exercises:
        debug_info.append({
            'id': ex.id,
            'title': ex.title,
            'type': ex.exercise_type,
            'content': ex.content,
            'parsed_content': ex.get_content()
        })
    
    return render_template('debug_exercises.html', exercises=debug_info)

@app.route('/debug/images')
def debug_images():
    # Lister tous les fichiers dans le dossier uploads
    files = []
    upload_dir = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_dir):
        if filename.startswith('pair_left_'):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                files.append({
                    'name': filename,
                    'url': url_for('static', filename=f'uploads/{filename}'),
                    'size': os.path.getsize(file_path)
                })
    
    return render_template('debug_images.html', files=files)

import random

def generate_word_search_grid(words, max_attempts=3):
    """Génère une grille de mots mêlés à partir d'une liste de mots."""
    if not words:
        return None
        
    # Normaliser les mots (majuscules, pas d'espaces)
    words = [word.strip().upper() for word in words]
    
    # Vérifier la validité des mots
    if any(not word.isalpha() for word in words):
        raise ValueError("Les mots ne doivent contenir que des lettres")
    
    # Trouver la taille de la grille nécessaire
    max_length = max(len(word) for word in words)
    grid_size = max(15, max_length + 2)  # Au moins 15x15 ou assez grand pour le plus long mot
    
    # Directions possibles pour placer les mots
    directions = [
        (0, 1),   # horizontal
        (1, 0),   # vertical
        (1, 1),   # diagonal bas-droite
        (-1, 1),  # diagonal haut-droite
    ]
    
    def can_place_word(grid, word, start_x, start_y, dx, dy):
        """Vérifie si un mot peut être placé à partir d'une position donnée."""
        for i, letter in enumerate(word):
            x = start_x + i * dx
            y = start_y + i * dy
            if not (0 <= x < grid_size and 0 <= y < grid_size):
                return False
            if grid[y][x] and grid[y][x] != letter:
                return False
        return True
    
    def place_word(grid, word):
        """Tente de placer un mot dans la grille."""
        attempts = 100  # Nombre maximum d'essais par mot
        while attempts > 0:
            dx, dy = random.choice(directions)
            if dx == 0:  # horizontal
                x = random.randint(0, grid_size - len(word))
                y = random.randint(0, grid_size - 1)
            elif dy == 0:  # vertical
                x = random.randint(0, grid_size - 1)
                y = random.randint(0, grid_size - len(word))
            else:  # diagonal
                x = random.randint(0, grid_size - len(word))
                y = random.randint(0, grid_size - len(word))
            
            if can_place_word(grid, word, x, y, dx, dy):
                for i, letter in enumerate(word):
                    grid[y + i * dy][x + i * dx] = letter
                return True
            attempts -= 1
        return False
    
    # Essayer de générer une grille valide
    attempt_count = 0
    while attempt_count < max_attempts:
        try:
            # Créer une grille vide
            grid = [['' for _ in range(grid_size)] for _ in range(grid_size)]
            
            # Placer chaque mot
            random.shuffle(words)  # Mélanger les mots pour varier leur placement
            success = True
            for word in words:
                if not place_word(grid, word):
                    success = False
                    break
            
            if success:
                # Remplir les cases vides avec des lettres aléatoires
                letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                for y in range(grid_size):
                    for x in range(grid_size):
                        if not grid[y][x]:
                            grid[y][x] = random.choice(letters)
                return grid
        except Exception:
            pass
            
        attempt_count += 1
    
    return None  # Si on n'a pas réussi à générer une grille valide

@app.route('/exercise/<int:exercise_id>/attempt/<int:attempt_id>')
@login_required
def view_attempt(exercise_id, attempt_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    attempt = ExerciseAttempt.query.get_or_404(attempt_id)
    course_id = request.args.get('course_id', type=int)
    course = Course.query.get(course_id) if course_id else None
    
    # Vérifier que la tentative appartient à l'exercice
    if attempt.exercise_id != exercise_id:
        flash('Cette tentative ne correspond pas à cet exercice.', 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))
    
    # Si c'est un professeur
    if current_user.is_teacher:
        # Vérifier que l'exercice appartient au professeur
        if exercise.teacher_id != current_user.id:
            flash('Vous n\'êtes pas autorisé à voir cette tentative.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id))
    # Si c'est un élève
    else:
        # Vérifier que la tentative appartient bien à l'élève
        if attempt.student_id != current_user.id:
            flash('Vous n\'êtes pas autorisé à voir cette tentative.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id))
    
    # Récupérer le contenu de l'exercice
    content = exercise.get_content()
    if not content:
        flash('Impossible de récupérer le contenu de l\'exercice.', 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))
    
    return render_template('view_attempt.html', 
                         exercise=exercise, 
                         attempt=attempt,
                         course=course,
                         content=content)



@app.route('/exercise/<int:exercise_id>/delete', methods=['POST'])
@login_required
def delete_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Vérifier que l'utilisateur est l'enseignant qui a créé l'exercice
    if not current_user.is_teacher or (current_user.id != exercise.teacher_id):
        flash('Vous n\'avez pas la permission de supprimer cet exercice.', 'error')
        return redirect(url_for('exercise_library'))
    
    # Supprimer toutes les tentatives liées à cet exercice
    ExerciseAttempt.query.filter_by(exercise_id=exercise.id).delete()
    
    # Supprimer l'exercice
    db.session.delete(exercise)
    db.session.commit()
    
    flash('Exercice supprimé avec succès !', 'success')
    return redirect(url_for('exercise_library'))

@app.route('/exercise/<int:exercise_id>/submit', methods=['POST'])
@login_required
def submit_exercise_answer(exercise_id):
    try:
        exercise = Exercise.query.get_or_404(exercise_id)
        course_id = request.form.get('course_id')
        course = Course.query.get(course_id) if course_id else None
        
        # Vérifier que l'étudiant a accès à l'exercice si c'est via un cours
        if course and current_user.role == 'student':
            class_obj = Class.query.get(course.class_id)
            if not class_obj or current_user not in class_obj.students:
                flash('Vous n\'avez pas accès à cet exercice.', 'error')
                return redirect(url_for('index'))
        
        # Récupérer les réponses et calculer le score pour underline_words
        answers = {}
        score = 0
        max_score = 0
        feedback = {}
        if exercise.exercise_type == 'underline_words':
            content = json.loads(exercise.content)
            for i, sentence in enumerate(content['sentences']):
                # Récupération de la sélection côté utilisateur (format indices ou texte)
                selected_raw = request.form.get(f'selected_words_{i}', '')
                selected_list = []
                if selected_raw:
                    try:
                        # Essayer de décoder comme JSON (indices)
                        selected_list = json.loads(selected_raw)
                        # Si ce sont des indices, convertir en texte
                        if all(isinstance(idx, int) for idx in selected_list):
                            selected_words = [sentence['words'][idx] for idx in selected_list if 0 <= idx < len(sentence['words'])]
                        else:
                            selected_words = [str(w) for w in selected_list]
                    except Exception:
                        # Sinon, séparer par virgule (texte)
                        selected_words = [w.strip() for w in selected_raw.split(',') if w.strip()]
                else:
                    selected_words = []
                answers[f'sentence_{i}'] = selected_words

                # DEBUG LOGS
                app.logger.info(f"[underline_words] Phrase {i} :")
                app.logger.info(f"  - Mots attendus (words_to_underline): {sentence['words_to_underline']}")
                app.logger.info(f"  - Mots sélectionnés (brut): {selected_words}")

                correct_words = set(word.lower().strip() for word in sentence['words_to_underline'])
                student_words = set(word.lower().strip() for word in selected_words)
                app.logger.info(f"  - Mots attendus (normalisés): {correct_words}")
                app.logger.info(f"  - Mots sélectionnés (normalisés): {student_words}")

                max_sentence_score = len(correct_words)
                correct_matches = correct_words & student_words
                incorrect_words = student_words - correct_words
                sentence_score = max(0, len(correct_matches) - len(incorrect_words))
                app.logger.info(f"  - Mots corrects trouvés: {correct_matches}")
                app.logger.info(f"  - Mots incorrects: {incorrect_words}")
                app.logger.info(f"  - Score phrase: {sentence_score}/{max_sentence_score}")
                score += sentence_score
                max_score += max_sentence_score
                feedback[f'sentence_{i}'] = {
                    'correct_words': list(correct_words),
                    'student_words': list(student_words),
                    'score': sentence_score,
                    'max_score': max_sentence_score
                }
        
        # Créer une nouvelle tentative
        # Pour drag_and_drop, feedback est feedback_summary (sinon feedback dict habituel)
        if exercise.exercise_type == 'drag_and_drop':
            feedback_to_save = feedback_summary
        else:
            feedback_to_save = feedback
        attempt = ExerciseAttempt(
            exercise_id=exercise_id,
            student_id=current_user.id,
            answers=json.dumps(answers),
            score=score,
            max_score=max_score,
            feedback=json.dumps(feedback_to_save)
        )
        
        try:
            db.session.add(attempt)
            db.session.commit()
            flash(f'Réponses enregistrées ! Score : {score}/{max_score}', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'enregistrement de votre tentative.', 'error')
            app.logger.error(f'Erreur lors de l\'enregistrement de la tentative : {str(e)}')
        
        return redirect(url_for('view_exercise', exercise_id=exercise_id))
    except Exception as e:
        app.logger.error(f'Erreur lors de la soumission de l\'exercice : {str(e)}')
        flash('Une erreur est survenue lors de la soumission de l\'exercice.', 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))

        # Récupérer les réponses en fonction du type d'exercice
        if exercise.exercise_type == 'qcm':
            answers = []
            correct_answers = []
            for i, question in enumerate(content['questions']):
                user_answer = request.form.get(f'answer_{i}')
                if user_answer is None:
                    flash('Veuillez répondre à toutes les questions.', 'error')
                    return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
                user_answer = int(user_answer)
                correct_answer = question['correct_answer']
                app.logger.info(f"Question {i} - User answer: '{user_answer}' (type: {type(user_answer)}), Correct answer: '{correct_answer}' (type: {type(correct_answer)})")
                answers.append(user_answer)
                correct_answers.append(correct_answer)
            
            # Vérifier chaque réponse individuellement pour le débogage
            score = 0
            for i, (user_ans, correct_ans) in enumerate(zip(answers, correct_answers)):
                is_correct = user_ans == correct_ans
                app.logger.info(f"Comparing Q{i}: '{user_ans}' == '{correct_ans}' -> {is_correct}")
                if is_correct:
                    score += 1
            
            max_score = len(content['questions'])
            
        elif exercise.exercise_type == 'fill_in_blanks':
            answers = []
            correct_answers = []
            score = 0
            
            app.logger.info(f"Processing fill_in_blanks exercise {exercise_id}")
            app.logger.info(f"Content: {content}")
            
            for i, sentence in enumerate(content['sentences']):
                user_answer = request.form.get(f'answer_{i}', '').strip()
                correct_answer = sentence['answer'].strip()
                
                answers.append(user_answer)
                correct_answers.append(correct_answer)
                
                app.logger.info(f"Question {i}:")
                app.logger.info(f"- User answer: '{user_answer}'")
                app.logger.info(f"- Correct answer: '{correct_answer}'")
                
                if user_answer.lower() == correct_answer.lower():
                    score += 1
                    app.logger.info(f"- Correct!")
                else:
                    app.logger.info(f"- Incorrect")
            
            max_score = len(content['sentences'])
            app.logger.info(f"Final score: {score}/{max_score}")

        elif exercise.exercise_type == 'pairs':
            user_pairs = []
            i = 0
            while f'left_{i}' in request.form and f'right_{i}' in request.form:
                left = int(request.form[f'left_{i}'])
                right = int(request.form[f'right_{i}'])
                user_pairs.append([left, right])
                i += 1
            correct_pairs = content['correct_pairs']
            score = sum(1 for pair in user_pairs if pair in correct_pairs)
            max_score = len(correct_pairs)

        elif exercise.exercise_type == 'drag_and_drop':
            user_order = []
            feedback = []
            for i in range(len(content['draggable_items'])):
                val = request.form.get(f'answer_{i}')
                try:
                    idx = int(val)
                    user_order.append(idx)
                except (ValueError, TypeError):
                    user_order.append(-1)
            correct_order = content.get('correct_order', [])
            score_count = 0
            for i, (user_idx, correct_idx) in enumerate(zip(user_order, correct_order)):
                user_item = content['draggable_items'][user_idx] if 0 <= user_idx < len(content['draggable_items']) else None
                correct_item = content['draggable_items'][correct_idx] if 0 <= correct_idx < len(content['draggable_items']) else None
                is_correct = user_idx == correct_idx
                feedback.append({
                    'zone': i+1,
                    'expected': correct_item,
                    'given': user_item,
                    'is_correct': is_correct
                })
                if is_correct:
                    score_count += 1
            max_score = len(correct_order)
            score = (score_count / max_score) * 100 if max_score > 0 else 0
            # Ajout du score global dans le feedback
            feedback_summary = {
                'score': score,
                'score_count': score_count,
                'max_score': max_score,
                'details': feedback
            }
            
        # Bloc supprimé car redondant, voir bloc unifié ci-dessus



@app.route('/exercise/preview/<int:exercise_id>')
@login_required
def preview_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    content = exercise.get_content()
    
    # Initialiser le contenu par défaut si nécessaire
    if not content:
        content = {}
    
    # Initialiser le contenu en fonction du type d'exercice
    if exercise.exercise_type == 'underline_words':
        if 'sentences' not in content:
            content['sentences'] = []
        # Convertir les phrases en format adapté au template
        for i, sentence in enumerate(content['sentences']):
            if isinstance(sentence, str):
                content['sentences'][i] = {
                    'text': sentence,
                    'words': sentence.split(),
                    'words_to_underline': []
                }
    elif exercise.exercise_type == 'pairs':
        if 'left_items' not in content:
            content['left_items'] = []
        if 'right_items' not in content:
            content['right_items'] = []
        if 'correct_pairs' not in content:
            content['correct_pairs'] = []
    elif exercise.exercise_type == 'qcm':
        if 'questions' not in content:
            content['questions'] = []
        # S'assurer que chaque question a la bonne structure
        for i, question in enumerate(content.get('questions', [])):
            if isinstance(question, dict):
                if 'text' not in question:
                    question['text'] = ''
                if 'choices' not in question:
                    question['choices'] = []
                if 'correct_answer' not in question:
                    question['correct_answer'] = 0
    
    # Choisir le template en fonction du type d'exercice
    template = f'exercise_types/{exercise.exercise_type}.html'
    
    return render_template(template, exercise=exercise, content=content)






# Route supprimée car dupliquée avec /exercise/create

if __name__ == '__main__':
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()
        
    app.run(debug=True)
