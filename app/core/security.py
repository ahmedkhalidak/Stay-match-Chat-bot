from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel
import jwt
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)

# كلمات ممنوعة — بيانات حساسة
_SENSITIVE = [
    "password", "passwd", "باسورد",
    "credit card", "cvv", "ssn", "رقم قومي",
    "api_key", "secret", "token",
]

# أوامر SQL خطرة
_SQL_INJECT = [
    "drop ", "delete ", "insert ", "update ",
    "exec(", "xp_", "union select", "'; ",
]


def sanitize(text: str) -> str:
    """
    يتحقق من النص ويرفضه لو فيه:
    - بيانات حساسة
    - SQL injection محتمل
    """
    low = text.lower()

    for term in _SENSITIVE:
        if term in low:
            raise HTTPException(status_code=400, detail="الرسالة تحتوي على كلمات غير مسموح بها.")

    for cmd in _SQL_INJECT:
        if cmd in low:
            raise HTTPException(status_code=400, detail="مدخل غير صالح.")

    # حد النص
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="الرسالة فاضية.")

    return cleaned


class CurrentUser(BaseModel):
    """Current authenticated user from JWT."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """
    Extract and validate JWT token from Authorization header.
    
    Returns CurrentUser with user_id extracted from JWT claims.
    
    Raises HTTPException with 401 status if:
    - Token is missing
    - Token is invalid
    - Token is expired
    - Token signature is invalid
    - Required claims are missing
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = credentials.credentials
    
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    
    # Extract user_id from JWT claims
    # Try multiple possible claim names for user_id
    user_id = (
        payload.get("sub") or
        payload.get("user_id") or
        payload.get("userId") or
        payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
    )
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing required claim: user_id")
    
    # Extract optional claims
    email = payload.get("email") or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
    name = payload.get("name") or payload.get("unique_name") or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
    
    return CurrentUser(
        user_id=str(user_id),
        email=email,
        name=name,
    )