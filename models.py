import bcrypt
from datetime import datetime
from database import db
import logging

class Utilisateur:
    def __init__(self, id=None, data=None):
        self.id = id
        self.data = data
        if id and not data:
            self._load()
    
    def _load(self):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM utilisateurs WHERE id = %s", (self.id,))
            self.data = cursor.fetchone()
    
    @staticmethod
    def get_by_email(email):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
            return cursor.fetchone()
    
    @staticmethod
    def create(prenom, email, mot_de_passe, genre, age, ville, profession=None, bio=None):
        hashed = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt())
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO utilisateurs 
                    (prenom, email, mot_de_passe, genre, age, ville, profession, bio)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (prenom, email, hashed.decode('utf-8'), genre, age, ville, profession, bio))
                user_id = cursor.lastrowid
                return user_id
    
    @staticmethod
    def authenticate(email, mot_de_passe):
        user = Utilisateur.get_by_email(email)
        if user and bcrypt.checkpw(mot_de_passe.encode('utf-8'), user['mot_de_passe'].encode('utf-8')):
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE utilisateurs 
                    SET derniere_connexion = NOW(), statut = 'en_ligne' 
                    WHERE id = %s
                """, (user['id'],))
            return user
        return None
    
    def get_matchs(self):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT m.*, 
                    u.id as autre_id, u.prenom, u.age, u.ville, u.photo_profil, u.statut,
                    (SELECT COUNT(*) FROM messages 
                     WHERE match_id = m.id AND lu = 0 AND destinataire_id = %s) as non_lus
                FROM matchs m
                JOIN utilisateurs u ON (u.id = CASE 
                    WHEN m.utilisateur1_id = %s THEN m.utilisateur2_id 
                    ELSE m.utilisateur1_id 
                END)
                WHERE (m.utilisateur1_id = %s OR m.utilisateur2_id = %s)
                  AND m.statut = 'accepte'
                ORDER BY m.date_match DESC
            """, (self.id, self.id, self.id, self.id))
            return cursor.fetchall()
    
    def get_messages(self, match_id):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE match_id = %s 
                ORDER BY date_envoi ASC
            """, (match_id,))
            return cursor.fetchall()
    
    def send_message(self, match_id, destinataire_id, contenu):
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO messages (match_id, expediteur_id, destinataire_id, contenu)
                    VALUES (%s, %s, %s, %s)
                """, (match_id, self.id, destinataire_id, contenu))
                return cursor.lastrowid
    
    def mark_messages_read(self, match_id):
        with db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE messages 
                SET lu = 1, date_lu = NOW() 
                WHERE match_id = %s AND destinataire_id = %s AND lu = 0
            """, (match_id, self.id))
    
    def get_likes_recus(self):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT l.*, u.prenom, u.age, u.ville, u.photo_profil
                FROM likes l
                JOIN utilisateurs u ON u.id = l.likeur_id
                WHERE l.like_id = %s AND l.type IN ('like', 'super_like')
                ORDER BY l.date_like DESC
            """, (self.id,))
            return cursor.fetchall()
    
    def create_like(self, target_id, type_like='like'):
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Vérifier si un like existe déjà
                cursor.execute(
                    "SELECT * FROM likes WHERE likeur_id = %s AND like_id = %s",
                    (self.id, target_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute(
                        "UPDATE likes SET type = %s, date_like = NOW() WHERE id = %s",
                        (type_like, existing['id'])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO likes (likeur_id, like_id, type) VALUES (%s, %s, %s)",
                        (self.id, target_id, type_like)
                    )
                
                # Vérifier si c'est un match mutuel
                cursor.execute("""
                    SELECT * FROM likes 
                    WHERE likeur_id = %s AND like_id = %s AND type IN ('like', 'super_like')
                """, (target_id, self.id))
                mutual = cursor.fetchone()
                
                if mutual:
                    # Créer un match
                    cursor.execute("""
                        INSERT INTO matchs (utilisateur1_id, utilisateur2_id, statut) 
                        VALUES (%s, %s, 'accepte')
                    """, (self.id, target_id))
                    match_id = cursor.lastrowid
                    
                    # Notifications pour les deux utilisateurs
                    cursor.execute("""
                        INSERT INTO notifications (utilisateur_id, type, contenu) 
                        VALUES (%s, 'match', 'Vous avez un nouveau match !')
                    """, (target_id,))
                    cursor.execute("""
                        INSERT INTO notifications (utilisateur_id, type, contenu) 
                        VALUES (%s, 'match', 'Vous avez un nouveau match !')
                    """, (self.id,))
                    
                    return {'match': True, 'match_id': match_id}
                
                return {'match': False}
    
    def update_profil(self, data):
        allowed_fields = ['prenom', 'age', 'ville', 'profession', 'bio', 'orientation', 'recherche']
        updates = []
        values = []
        
        for key, value in data.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(self.id)
        with db.get_cursor() as cursor:
            cursor.execute(
                f"UPDATE utilisateurs SET {', '.join(updates)} WHERE id = %s",
                values
            )
            return True
    
    def update_interets(self, interet_ids):
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Supprimer les anciens
                cursor.execute(
                    "DELETE FROM utilisateur_interets WHERE utilisateur_id = %s",
                    (self.id,)
                )
                
                # Ajouter les nouveaux
                if interet_ids:
                    for interet_id in interet_ids:
                        cursor.execute(
                            "INSERT INTO utilisateur_interets (utilisateur_id, interet_id) VALUES (%s, %s)",
                            (self.id, interet_id)
                        )
                return True
    
    def get_interets(self):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT i.* 
                FROM centres_interet i
                JOIN utilisateur_interets ui ON ui.interet_id = i.id
                WHERE ui.utilisateur_id = %s
            """, (self.id,))
            return cursor.fetchall()
    
    def get_profils_a_swiper(self, age_min=18, age_max=99, limit=20):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT u.*, 
                    (SELECT COUNT(*) FROM likes WHERE likeur_id = %s AND like_id = u.id) as deja_like,
                    (SELECT COUNT(*) FROM likes WHERE likeur_id = u.id AND like_id = %s) as a_aime
                FROM utilisateurs u
                WHERE u.id != %s
                  AND u.compte_actif = 1
                  AND u.age BETWEEN %s AND %s
                ORDER BY RAND()
                LIMIT %s
            """, (self.id, self.id, self.id, age_min, age_max, limit))
            return cursor.fetchall()
    
    def logout(self):
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE utilisateurs SET statut = 'hors_ligne' WHERE id = %s",
                (self.id,)
            )
    
    def get_notifications(self, limit=50):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE utilisateur_id = %s 
                ORDER BY date_creation DESC 
                LIMIT %s
            """, (self.id, limit))
            return cursor.fetchall()
    
    def mark_notifications_read(self):
        with db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE notifications 
                SET lue = 1 
                WHERE utilisateur_id = %s AND lue = 0
            """, (self.id,))

class Match:
    @staticmethod
    def get_or_create(user1_id, user2_id):
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM matchs 
                WHERE (utilisateur1_id = %s AND utilisateur2_id = %s)
                   OR (utilisateur1_id = %s AND utilisateur2_id = %s)
            """, (user1_id, user2_id, user2_id, user1_id))
            match = cursor.fetchone()
            
            if match:
                return match
            
            cursor.execute("""
                INSERT INTO matchs (utilisateur1_id, utilisateur2_id, statut)
                VALUES (%s, %s, 'en_attente')
            """, (user1_id, user2_id))
            return {'id': cursor.lastrowid, 'statut': 'en_attente'}

# Initialisation des centres d'intérêt
def init_interets():
    interets = [
        ('Art', '🎨', 'créatif'),
        ('Voyage', '✈️', 'aventure'),
        ('Musique', '🎵', 'culturel'),
        ('Cinéma', '🎬', 'culturel'),
        ('Sport', '🏃', 'sportif'),
        ('Lecture', '📚', 'intellectuel'),
        ('Cuisine', '🍳', 'gastronomique'),
        ('Nature', '🌿', 'plein_air'),
        ('Photographie', '📷', 'créatif'),
        ('Animaux', '🐾', 'nature'),
        ('Jeux vidéo', '🎮', 'divertissement'),
        ('Danse', '💃', 'artistique'),
    ]
    
    with db.get_cursor() as cursor:
        for nom, icone, categorie in interets:
            try:
                cursor.execute(
                    "INSERT INTO centres_interet (nom, icone, categorie) VALUES (%s, %s, %s)",
                    (nom, icone, categorie)
                )
            except:
                pass