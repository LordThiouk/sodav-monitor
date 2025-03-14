"""Configuration des tests pour le projet SODAV Monitor."""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Generator, List

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import get_settings, settings
from backend.main import app
from backend.models.database import Base, TestingSessionLocal, get_db, test_engine

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

# Fixtures de base pour tous les tests

@pytest.fixture(scope="session")
def test_app():
    """Fixture pour l'application FastAPI de test."""
    return app

@pytest.fixture(scope="session")
def client():
    """Fixture pour le client de test FastAPI."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="function")
def db():
    """Fixture pour la session de base de données de test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Début de la transaction
    yield session

    # Rollback après le test
    session.close()
    transaction.rollback()
    connection.close()

# Importation des fixtures spécifiques aux modules
# Ces importations permettent de rendre disponibles les fixtures définies dans les sous-modules

try:
    from backend.tests.unit.utils.conftest import *  # noqa
except ImportError:
    pass

try:
    from backend.tests.unit.analytics.conftest import *  # noqa
except ImportError:
    pass

try:
    from backend.tests.unit.detection.conftest import *  # noqa
except ImportError:
    pass

try:
    from backend.tests.integration.conftest import *  # noqa
except ImportError:
    pass

# Autres fixtures communes peuvent être ajoutées ici
