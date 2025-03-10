#!/usr/bin/env python3
"""
Script pour créer un utilisateur administrateur dans la base de données SODAV Monitor.
"""
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modèles après avoir ajusté le chemin
from backend.models.models import Base, User
from backend.models.database import get_database_url

# Configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user(username, email, password):
    """Crée un utilisateur administrateur dans la base de données."""
    # Obtenir l'URL de la base de données
    database_url = get_database_url()
    
    # Créer le moteur de base de données
    engine = create_engine(database_url)
    
    # Créer une session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"Un utilisateur avec ce nom d'utilisateur ou cet email existe déjà: {username} / {email}")
            return False
        
        # Créer un nouvel utilisateur administrateur
        hashed_password = pwd_context.hash(password)
        admin_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_active=True,
            role="admin",
            created_at=datetime.utcnow()
        )
        
        # Ajouter l'utilisateur à la base de données
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"Utilisateur administrateur créé avec succès: {username}")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de la création de l'utilisateur: {str(e)}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    # Paramètres par défaut
    default_username = "admin"
    default_email = "admin@sodav.sn"
    default_password = "admin123"
    
    # Utiliser les paramètres par défaut ou les arguments de ligne de commande
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
    else:
        username = default_username
        email = default_email
        password = default_password
        print(f"Utilisation des paramètres par défaut: {username} / {email} / {password}")
    
    # Créer l'utilisateur administrateur
    success = create_admin_user(username, email, password)
    
    if success:
        print("Utilisateur administrateur créé avec succès.")
    else:
        print("Échec de la création de l'utilisateur administrateur.") 