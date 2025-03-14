#!/usr/bin/env python3
"""
Script to create an admin user in the database.
"""

import getpass
import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from models.database import get_db, init_db
from models.models import User
from sqlalchemy.orm import Session
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
            created_at=datetime.utcnow(),
        )

        # Add and commit to the database
        db_session.add(admin_user)
        db_session.commit()

        logger.info(f"Admin user {username} created successfully.")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise


if __name__ == "__main__":
    # Get admin credentials from environment variables or prompt user
    default_username = os.environ.get("ADMIN_USERNAME", "admin")
    default_email = os.environ.get("ADMIN_EMAIL", "admin@sodav.sn")

    # Use environment variable for password if available, otherwise prompt
    if "ADMIN_PASSWORD" in os.environ:
        default_password = os.environ["ADMIN_PASSWORD"]
    else:
        print("No ADMIN_PASSWORD environment variable found.")
        default_password = getpass.getpass("Enter admin password: ")

        # Confirm password
        confirm_password = getpass.getpass("Confirm admin password: ")
        if default_password != confirm_password:
            logger.error("Passwords do not match. Exiting.")
            sys.exit(1)

    # Allow overriding from command line
    if len(sys.argv) > 3:
        default_username = sys.argv[1]
        default_email = sys.argv[2]
        default_password = sys.argv[3]
        logger.warning(
            "Using command line arguments for credentials is not secure. Consider using environment variables instead."
        )

    if not default_password or default_password.strip() == "":
        logger.error("Password cannot be empty. Exiting.")
        sys.exit(1)

    create_admin_user(default_username, default_email, default_password)
