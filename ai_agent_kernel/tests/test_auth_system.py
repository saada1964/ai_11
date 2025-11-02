"""
Comprehensive test suite for the authentication system
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone, timedelta
import json

from main import app
from database.database import get_db, Base
from models.models import User, ActiveSession
from services.auth_service import AuthService
from utils.security import SecurityUtils, JWTManager
from config.settings import settings


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_auth.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Set up test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Basemeta_data.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Basemeta_data.drop_all)


@pytest.fixture
async def db_session():
    """Create a test database session"""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def test_user(db_session):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=SecurityUtils.hash_password("testpassword123"),
        balance=100000,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestSecurityUtils:
    """Test security utilities"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = SecurityUtils.hash_password(password)
        
        assert hashed != password
        assert SecurityUtils.verify_password(password, hashed)
        assert not SecurityUtils.verify_password("wrongpassword", hashed)
    
    def test_token_generation(self):
        """Test secure token generation"""
        token1 = SecurityUtils.generate_secure_token()
        token2 = SecurityUtils.generate_secure_token()
        
        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        # Valid password
        is_valid, message = SecurityUtils.validate_password_strength("Test123!@#")
        assert is_valid
        
        # Too short
        is_valid, message = SecurityUtils.validate_password_strength("Test123")
        assert not is_valid
        assert "8 characters" in message
        
        # No uppercase
        is_valid, message = SecurityUtils.validate_password_strength("test123!@#")
        assert not is_valid
        assert "uppercase" in message
        
        # No special characters
        is_valid, message = SecurityUtils.validate_password_strength("Test123456")
        assert not is_valid
        assert "special character" in message


class TestJWTManager:
    """Test JWT token management"""
    
    def test_access_token_creation_and_verification(self):
        """Test access token creation and verification"""
        data = {"sub": "123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
        
        # Verify token
        payload = JWTManager.verify_token(token, "access")
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_refresh_token_creation_and_verification(self):
        """Test refresh token creation and verification"""
        data = {"sub": "123", "session_id": 456}
        token = JWTManager.create_refresh_token(data)
        
        assert token is not None
        assert len(token) > 0
        
        # Verify token
        payload = JWTManager.verify_token(token, "refresh")
        assert payload["sub"] == "123"
        assert payload["session_id"] == 456
        assert payload["type"] == "refresh"
    
    def test_token_expiration(self):
        """Test token expiration"""
        # Create token with very short expiration
        data = {"sub": "123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = JWTManager.create_access_token(data, expires_delta)
        
        # Should raise exception for expired token
        with pytest.raises(Exception):
            JWTManager.verify_token(token, "access")
    
    def test_invalid_token_type(self):
        """Test invalid token type verification"""
        data = {"sub": "123"}
        access_token = JWTManager.create_access_token(data)
        
        # Should raise exception when verifying access token as refresh
        with pytest.raises(Exception):
            JWTManager.verify_token(access_token, "refresh")


class TestAuthService:
    """Test authentication service"""
    
    @pytest.mark.asyncio
    async def test_user_registration(self, db_session):
        """Test user registration"""
        from schemas.auth_schemas import UserRegister
        
        auth_service = AuthService(db_session)
        user_data = UserRegister(
            username="newuser",
            email="newuser@example.com",
            password="NewPassword123!"
        )
        
        user = await auth_service.register_user(user_data)
        
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.balance == 100000
    
    @pytest.mark.asyncio
    async def test_duplicate_user_registration(self, db_session, test_user):
        """Test duplicate user registration fails"""
        from schemas.auth_schemas import UserRegister
        
        auth_service = AuthService(db_session)
        user_data = UserRegister(
            username="testuser",  # Same as test_user
            email="test@example.com",  # Same as test_user
            password="Password123!"
        )
        
        with pytest.raises(Exception):
            await auth_service.register_user(user_data)
    
    @pytest.mark.asyncio
    async def test_user_authentication_success(self, db_session, test_user):
        """Test successful user authentication"""
        from schemas.auth_schemas import UserLogin
        from unittest.mock import Mock
        
        auth_service = AuthService(db_session)
        credentials = UserLogin(
            email="test@example.com",
            password="testpassword123"
        )
        
        # Mock request object
        request = Mock()
        request.headers = {"User-Agent": "Test Client"}
        request.client.host = "127.0.0.1"
        
        tokens = await auth_service.authenticate_user(credentials, request)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.user.email == "test@example.com"
        assert tokens.token_type == "bearer"
    
    @pytest.mark.asyncio
    async def test_user_authentication_failure(self, db_session, test_user):
        """Test failed user authentication"""
        from schemas.auth_schemas import UserLogin
        from unittest.mock import Mock
        
        auth_service = AuthService(db_session)
        credentials = UserLogin(
            email="test@example.com",
            password="wrongpassword"
        )
        
        request = Mock()
        request.headers = {"User-Agent": "Test Client"}
        request.client.host = "127.0.0.1"
        
        with pytest.raises(Exception):
            await auth_service.authenticate_user(credentials, request)
    
    @pytest.mark.asyncio
    async def test_password_change(self, db_session, test_user):
        """Test password change"""
        auth_service = AuthService(db_session)
        
        success = await auth_service.change_password(
            user_id=test_user.id,
            current_password="testpassword123",
            new_password="NewPassword123!"
        )
        
        assert success is True
        
        # Verify old password no longer works
        from schemas.auth_schemas import UserLogin
        from unittest.mock import Mock
        
        credentials = UserLogin(
            email="test@example.com",
            password="testpassword123"  # Old password
        )
        
        request = Mock()
        request.headers = {"User-Agent": "Test Client"}
        request.client.host = "127.0.0.1"
        
        with pytest.raises(Exception):
            await auth_service.authenticate_user(credentials, request)


class TestAuthAPI:
    """Test authentication API endpoints"""
    
    def test_register_endpoint(self, client):
        """Test user registration endpoint"""
        response = client.post("/auth/register", json={
            "username": "apiuser",
            "email": "apiuser@example.com",
            "password": "ApiPassword123!"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "apiuser@example.com"
    
    def test_register_invalid_password(self, client):
        """Test registration with invalid password"""
        response = client.post("/auth/register", json={
            "username": "apiuser2",
            "email": "apiuser2@example.com",
            "password": "weak"  # Too weak
        })
        
        assert response.status_code == 400
    
    def test_login_endpoint(self, client):
        """Test user login endpoint"""
        # First register a user
        client.post("/auth/register", json={
            "username": "loginuser",
            "email": "loginuser@example.com",
            "password": "LoginPassword123!"
        })
        
        # Then login
        response = client.post("/auth/login", json={
            "email": "loginuser@example.com",
            "password": "LoginPassword123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_token(self, client):
        """Test accessing protected endpoint with valid token"""
        # Register and get token
        register_response = client.post("/auth/register", json={
            "username": "protecteduser",
            "email": "protecteduser@example.com",
            "password": "ProtectedPassword123!"
        })
        
        token = register_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protecteduser@example.com"
    
    def test_refresh_token_endpoint(self, client):
        """Test refresh token endpoint"""
        # Register and get tokens
        register_response = client.post("/auth/register", json={
            "username": "refreshuser",
            "email": "refreshuser@example.com",
            "password": "RefreshPassword123!"
        })
        
        refresh_token = register_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_logout_endpoint(self, client):
        """Test logout endpoint"""
        # Register and get token
        register_response = client.post("/auth/register", json={
            "username": "logoutuser",
            "email": "logoutuser@example.com",
            "password": "LogoutPassword123!"
        })
        
        token = register_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/auth/logout",
            json={"logout_all": False},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWebSocketAuthentication:
    """Test WebSocket authentication"""
    
    @pytest.mark.asyncio
    async def test_websocket_authentication(self, db_session):
        """Test WebSocket authentication"""
        from websockets.websocket_server import WebSocketAuth
        
        # Create a user and token
        user = User(
            username="wsuser",
            email="ws@example.com",
            hashed_password=SecurityUtils.hash_password("wspassword123"),
            balance=100000,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create session
        from unittest.mock import Mock
        request = Mock()
        request.headers = {"User-Agent": "WebSocket Client"}
        request.client.host = "127.0.0.1"
        
        auth_service = AuthService(db_session)
        from schemas.auth_schemas import UserLogin
        credentials = UserLogin(email="ws@example.com", password="wspassword123")
        tokens = await auth_service.authenticate_user(credentials, request)
        
        # Test WebSocket authentication
        authenticated_user, session = await WebSocketAuth.authenticate_websocket(
            tokens.access_token, db_session
        )
        
        assert authenticated_user.id == user.id
        assert session is not None


class TestSessionManagement:
    """Test session management"""
    
    @pytest.mark.asyncio
    async def test_multiple_sessions(self, db_session, test_user):
        """Test multiple session creation and management"""
        from unittest.mock import Mock
        
        auth_service = AuthService(db_session)
        
        # Create multiple sessions
        request1 = Mock()
        request1.headers = {"User-Agent": "Client 1"}
        request1.client.host = "127.0.0.1"
        
        request2 = Mock()
        request2.headers = {"User-Agent": "Client 2"}
        request2.client.host = "192.168.1.1"
        
        from schemas.auth_schemas import UserLogin
        credentials = UserLogin(
            email=test_user.email,
            password="testpassword123"
        )
        
        tokens1 = await auth_service.authenticate_user(credentials, request1)
        tokens2 = await auth_service.authenticate_user(credentials, request2)
        
        # Get active sessions
        sessions = await auth_service.get_active_sessions(test_user.id)
        
        assert sessions.total_count >= 2
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, db_session, test_user):
        """Test expired session cleanup"""
        # This would test the cleanup of expired sessions
        # Implementation depends on your cleanup strategy
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])