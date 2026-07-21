from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_cors import CORS
from flask_session import Session
from config import Config
from models import Utilisateur, Match, init_interets
from database import db
import logging
import os
from datetime import timedelta
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialisation des sessions
Session(app)

# CORS
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# ============================================
# ROUTES - FICHIERS STATIQUES (HTML)
# ============================================

@app.route('/')
def index():
    """Rediriger vers la page d'accueil"""
    return redirect('/INDEX.HTML')

@app.route('/<path:filename>')
def serve_static(filename):
    """Servir les fichiers HTML statiques"""
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return jsonify({'error': 'Fichier non trouvé'}), 404

# ============================================
# INITIALISATION DE LA BASE DE DONNÉES
# ============================================

with app.app_context():
    try:
        init_interets()
        logger.info("Base de données initialisée avec succès")
    except Exception as e:
        logger.error(f"Erreur d'initialisation: {e}")

# ============================================
# MIDDLEWARE - Authentification
# ============================================

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Non authentifié'}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        return Utilisateur(session['user_id'])
    return None

# ============================================
# ROUTES - AUTHENTIFICATION
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    required = ['prenom', 'email', 'password', 'genre', 'age', 'ville']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'Le champ {field} est requis'}), 400
    
    if '@' not in data['email']:
        return jsonify({'success': False, 'message': 'Email invalide'}), 400
    
    if data['age'] < 18 or data['age'] > 99:
        return jsonify({'success': False, 'message': 'Âge invalide (18-99)'}), 400
    
    if len(data['password']) < 8:
        return jsonify({'success': False, 'message': 'Le mot de passe doit contenir au moins 8 caractères'}), 400
    
    existing = Utilisateur.get_by_email(data['email'])
    if existing:
        return jsonify({'success': False, 'message': 'Cet email est déjà utilisé'}), 400
    
    try:
        user_id = Utilisateur.create(
            data['prenom'],
            data['email'],
            data['password'],
            data['genre'],
            data['age'],
            data['ville'],
            data.get('profession'),
            data.get('bio')
        )
        
        if data.get('interets'):
            user = Utilisateur(user_id)
            user.update_interets(data['interets'])
        
        session['user_id'] = user_id
        
        return jsonify({
            'success': True,
            'message': 'Inscription réussie',
            'user_id': user_id
        })
    except Exception as e:
        logger.error(f"Erreur inscription: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'inscription'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Email et mot de passe requis'}), 400
    
    user = Utilisateur.authenticate(data['email'], data['password'])
    
    if user:
        session['user_id'] = user['id']
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Connexion réussie',
            'user': {
                'id': user['id'],
                'prenom': user['prenom'],
                'email': user['email'],
                'age': user['age'],
                'ville': user['ville'],
                'photo_profil': user.get('photo_profil')
            }
        })
    
    return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    user = get_current_user()
    if user:
        user.logout()
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})

@app.route('/api/me', methods=['GET'])
@require_auth
def get_me():
    user = get_current_user()
    if user:
        return jsonify({
            'success': True,
            'user': user.data
        })
    return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404

# ============================================
# ROUTES - PROFIL
# ============================================

@app.route('/api/profil/update', methods=['PUT'])
@require_auth
def update_profil():
    user = get_current_user()
    data = request.get_json()
    
    try:
        user.update_profil(data)
        return jsonify({'success': True, 'message': 'Profil mis à jour'})
    except Exception as e:
        logger.error(f"Erreur update profil: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'}), 500

@app.route('/api/profil/interets', methods=['PUT'])
@require_auth
def update_interets():
    user = get_current_user()
    data = request.get_json()
    
    if not data.get('interets'):
        return jsonify({'success': False, 'message': 'Liste d\'intérêts requise'}), 400
    
    try:
        user.update_interets(data['interets'])
        return jsonify({'success': True, 'message': 'Intérêts mis à jour'})
    except Exception as e:
        logger.error(f"Erreur update interets: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'}), 500

@app.route('/api/profil/interets', methods=['GET'])
@require_auth
def get_interets():
    user = get_current_user()
    return jsonify({
        'success': True,
        'interets': user.get_interets()
    })

# ============================================
# ROUTES - SWIPE
# ============================================

@app.route('/api/swipe/profils', methods=['GET'])
@require_auth
def get_profils():
    user = get_current_user()
    age_min = request.args.get('age_min', 18, type=int)
    age_max = request.args.get('age_max', 99, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    profils = user.get_profils_a_swiper(age_min, age_max, limit)
    return jsonify({
        'success': True,
        'profils': profils
    })

@app.route('/api/swipe/like', methods=['POST'])
@require_auth
def create_like():
    user = get_current_user()
    data = request.get_json()
    
    target_id = data.get('user_id')
    type_like = data.get('type', 'like')
    
    if not target_id:
        return jsonify({'success': False, 'message': 'ID utilisateur requis'}), 400
    
    if target_id == user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous aimer vous-même'}), 400
    
    try:
        result = user.create_like(target_id, type_like)
        
        # Si c'est un match, les notifications sont déjà créées dans models.py
        # Mais on peut ajouter une notification supplémentaire si besoin
        
        return jsonify({
            'success': True,
            'match': result.get('match', False),
            'match_id': result.get('match_id')
        })
    except Exception as e:
        logger.error(f"Erreur like: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors du like'}), 500

# ============================================
# ROUTES - MATCHS
# ============================================

@app.route('/api/matchs', methods=['GET'])
@require_auth
def get_matchs():
    user = get_current_user()
    matchs = user.get_matchs()
    return jsonify({
        'success': True,
        'matchs': matchs
    })

# ============================================
# ROUTES - MESSAGES
# ============================================

@app.route('/api/messages/<int:match_id>', methods=['GET'])
@require_auth
def get_messages(match_id):
    user = get_current_user()
    messages = user.get_messages(match_id)
    user.mark_messages_read(match_id)
    return jsonify({
        'success': True,
        'messages': messages
    })

@app.route('/api/messages/send', methods=['POST'])
@require_auth
def send_message():
    user = get_current_user()
    data = request.get_json()
    
    match_id = data.get('match_id')
    destinataire_id = data.get('destinataire_id')
    contenu = data.get('contenu')
    
    if not all([match_id, destinataire_id, contenu]):
        return jsonify({'success': False, 'message': 'Champs requis manquants'}), 400
    
    try:
        message_id = user.send_message(match_id, destinataire_id, contenu)
        return jsonify({
            'success': True,
            'message_id': message_id
        })
    except Exception as e:
        logger.error(f"Erreur envoi message: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi'}), 500

# ============================================
# ROUTES - NOTIFICATIONS
# ============================================

@app.route('/api/notifications', methods=['GET'])
@require_auth
def get_notifications():
    user = get_current_user()
    notifications = user.get_notifications()
    return jsonify({
        'success': True,
        'notifications': notifications
    })

@app.route('/api/notifications/read', methods=['POST'])
@require_auth
def mark_notifications_read():
    user = get_current_user()
    user.mark_notifications_read()
    return jsonify({'success': True, 'message': 'Notifications marquées comme lues'})

# ============================================
# ROUTES - PHOTOS
# ============================================

@app.route('/api/photo/upload', methods=['POST'])
@require_auth
def upload_photo():
    user = get_current_user()
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'Aucune photo envoyée'}), 400
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({'success': False, 'message': 'Fichier vide'}), 400
    
    # Créer le dossier uploads s'il n'existe pas
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Sauvegarder la photo
    filename = f"user_{user.id}_{int(datetime.now().timestamp())}.jpg"
    filepath = os.path.join(upload_dir, filename)
    photo.save(filepath)
    
    # Mettre à jour la photo de profil dans la base de données
    with db.get_cursor() as cursor:
        cursor.execute(
            "UPDATE utilisateurs SET photo_profil = %s WHERE id = %s",
            (f'/uploads/{filename}', user.id)
        )
    
    return jsonify({
        'success': True,
        'message': 'Photo uploadée avec succès',
        'photo_path': f'/uploads/{filename}'
    })

# ============================================
# ROUTES - SEARCH
# ============================================

@app.route('/api/search', methods=['GET'])
@require_auth
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'success': False, 'message': 'Minimum 2 caractères'}), 400
    
    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, prenom, age, ville, photo_profil
            FROM utilisateurs
            WHERE prenom LIKE %s
              AND compte_actif = 1
              AND id != %s
            LIMIT 20
        """, (f'%{query}%', session['user_id']))
        results = cursor.fetchall()
    
    return jsonify({
        'success': True,
        'results': results
    })

# ============================================
# ROUTES - NOTIFICATIONS EN TEMPS RÉEL (WebSocket)
# ============================================
# Note: Pour une vraie version en temps réel, il faudrait utiliser
# Flask-SocketIO. Pour l'instant, on utilise le polling.

@app.route('/api/notifications/unread', methods=['GET'])
@require_auth
def get_unread_notifications():
    user = get_current_user()
    notifications = user.get_notifications()
    unread = [n for n in notifications if not n.get('lue', False)]
    return jsonify({
        'success': True,
        'count': len(unread),
        'notifications': unread[:10]  # Limiter à 10 pour l'affichage
    })






@app.route('/api/utilisateurs', methods=['GET'])
@require_auth
def get_all_users():
    """Récupérer tous les utilisateurs (admin)"""
    user = get_current_user()
    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, prenom, age, ville, statut, photo_profil
            FROM utilisateurs
            WHERE id != %s AND compte_actif = 1
            ORDER BY id DESC
            LIMIT 50
        """, (user.id,))
        users = cursor.fetchall()
    return jsonify({
        'success': True,
        'users': users
    })
# ============================================
# START
# ============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)