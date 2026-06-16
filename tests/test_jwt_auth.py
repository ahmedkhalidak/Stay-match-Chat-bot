"""Unit tests for JWT authentication."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from datetime import datetime, timedelta
import jwt

from app.core.security import get_current_user, CurrentUser


class TestJWTAuthentication:
    @pytest.fixture
    def mock_settings(self):
        """Mock JWT settings."""
        with patch('app.core.security.settings') as mock:
            mock.jwt_secret = "test-secret-key"
            mock.jwt_issuer = "test-issuer"
            mock.jwt_audience = "test-audience"
            yield mock

    def test_valid_token(self, mock_settings):
        """Test successful token validation and user extraction."""
        # Create a valid JWT token
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "email": "test@example.com",
            "name": "Test User",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        # Call get_current_user
        user = get_current_user(mock_credentials)
        
        # Verify user data
        assert isinstance(user, CurrentUser)
        assert user.user_id == "63a0c0e9-1aa2-415b-81c5-2338ea8fb559"
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_token_with_nameidentifier_claim(self, mock_settings):
        """Test token with XML SOAP nameidentifier claim."""
        payload = {
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "test@example.com",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "Test User",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        user = get_current_user(mock_credentials)
        
        assert user.user_id == "63a0c0e9-1aa2-415b-81c5-2338ea8fb559"
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_expired_token(self, mock_settings):
        """Test expired token raises 401."""
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_signature(self, mock_settings):
        """Test token with invalid signature raises 401."""
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        # Sign with wrong secret
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    def test_missing_user_id_claim(self, mock_settings):
        """Test token without user_id claim raises 401."""
        payload = {
            "email": "test@example.com",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "missing required claim" in exc_info.value.detail.lower()

    def test_wrong_issuer(self, mock_settings):
        """Test token with wrong issuer raises 401."""
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "iss": "wrong-issuer",  # Wrong issuer
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)
        
        assert exc_info.value.status_code == 401

    def test_wrong_audience(self, mock_settings):
        """Test token with wrong audience raises 401."""
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "iss": "test-issuer",
            "aud": "wrong-audience",  # Wrong audience
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)
        
        assert exc_info.value.status_code == 401

    def test_optional_claims_missing(self, mock_settings):
        """Test token with only required claims (sub)."""
        payload = {
            "sub": "63a0c0e9-1aa2-415b-81c5-2338ea8fb559",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        user = get_current_user(mock_credentials)
        
        assert user.user_id == "63a0c0e9-1aa2-415b-81c5-2338ea8fb559"
        assert user.email is None
        assert user.name is None

    def test_user_id_claim_priority(self, mock_settings):
        """Test that 'sub' claim takes priority over other user_id claims."""
        payload = {
            "sub": "sub-user-id",
            "user_id": "user-id-claim",
            "userId": "userId-claim",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "nameidentifier-user-id",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        user = get_current_user(mock_credentials)
        
        # Should use 'sub' claim (first in priority list)
        assert user.user_id == "sub-user-id"

    def test_fallback_to_user_id_claim(self, mock_settings):
        """Test fallback to 'user_id' claim when 'sub' is missing."""
        payload = {
            "user_id": "user-id-claim",
            "iss": "test-issuer",
            "aud": "test-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        user = get_current_user(mock_credentials)
        
        assert user.user_id == "user-id-claim"
