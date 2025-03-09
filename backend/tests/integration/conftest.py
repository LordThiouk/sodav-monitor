"""
Fixtures for integration tests.

This module contains fixtures that are used across multiple integration test modules.
"""

import pytest
import asyncio
from typing import Dict, Generator, List, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.models.models import (
    User, Report, ReportSubscription, RadioStation, 
    Artist, Track, TrackDetection, AnalyticsData
)
from backend.models.database import get_db, TestingSessionLocal
from backend.main import app
from backend.utils.auth.auth import create_access_token, get_current_user, oauth2_scheme

@pytest.fixture(scope="function")
def db_session() -> Generator:
    """
    Creates a fresh database session for a test.

    This fixture can be used for all tests that need a database session.
    """
    # Create a new session
    session = TestingSessionLocal()
    
    # Create tables if they don't exist
    from sqlalchemy import text
    from backend.models.models import Base
    from backend.models.database import engine
    Base.metadata.create_all(bind=engine)
    
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """
    Creates a test user for integration tests.

    This fixture can be used for tests that require a user.
    """
    # Check if test user already exists
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    if user:
        return user
    
    # Create a new test user
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        is_active=True,
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> Dict[str, str]:
    """
    Creates authentication headers for integration tests.

    This fixture can be used for tests that require authentication.
    """
    access_token = create_access_token(
        data={"sub": test_user.email, "id": test_user.id},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def test_client(db_session: Session, test_user: User, auth_headers: Dict[str, str]) -> TestClient:
    """
    Creates a test client for integration tests.

    This fixture can be used for tests that require a test client with authentication.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override get_current_user to return the test user directly
    # This is an async function that will be called by FastAPI
    async def override_get_current_user(*args, **kwargs):
        return test_user
    
    # Override oauth2_scheme to return the token from auth_headers
    def override_oauth2_scheme():
        return auth_headers["Authorization"].split(" ")[1]
    
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    
    with TestClient(app) as client:
        # Add authentication headers to all requests
        client.headers.update(auth_headers)
        yield client
    
    # Clear dependency overrides after the test
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
def simple_test_client(auth_headers: Dict[str, str]) -> TestClient:
    """
    A simple test client that doesn't use dependency overrides.
    This is useful for testing endpoints that don't require authentication.
    """
    client = TestClient(app)
    # Update the headers with authentication information
    client.headers.update(auth_headers)
    yield client
