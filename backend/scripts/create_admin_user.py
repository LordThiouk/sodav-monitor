#!/usr/bin/env python3
"""
Script to create an admin user in the database.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from sqlalchemy.orm import Session
from models.models import User
from models.database import get_db, init_db
from utils.auth.auth import get_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user(username: str, email: str, password: str):
    """Create an admin user in the database."""
    try:
        # Initialize the database
        init_db()
        
        # Get a database session
        db_session = next(get_db())
        
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email == email).first()
        if existing_user:
            logger.info(f"User with email {email} already exists.")
            return
        
        # Create the user
        hashed_password = get_password_hash(password)
        admin_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_active=True,
            role="admin",
            created_at=datetime.utcnow()
        )
        
        # Add and commit to the database
        db_session.add(admin_user)
        db_session.commit()
        
        logger.info(f"Admin user {username} created successfully.")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise

if __name__ == "__main__":
    # Default admin credentials
    default_username = "admin"
    default_email = "admin@sodav.sn"
    default_password = "admin123"
    
    # Allow overriding from command line
    if len(sys.argv) > 3:
        default_username = sys.argv[1]
        default_email = sys.argv[2]
        default_password = sys.argv[3]
    
    create_admin_user(default_username, default_email, default_password) 