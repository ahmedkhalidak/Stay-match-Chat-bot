# JWT Authentication Refactor Documentation - StayMatch AI Service

## Overview

This document describes the JWT authentication refactor implemented for the StayMatch AI Service (Chat Bot). The refactor removes user_id from the chat request body and instead extracts the authenticated user from JWT tokens issued by the .NET Authentication Service.

## Goals

- Stop accepting user_id in chat request body
- Extract current authenticated user from JWT token
- Align with production-ready architecture
- Support Flutter app consumption pattern
- Enable Swagger authorization testing

## Implementation Details

### Configuration

Added JWT configuration to `app/core/config.py`:

```python
jwt_secret: str = ""
jwt_issuer: str = ""
jwt_audience: str = ""
```

These values are read from environment variables:
- `JWT_SECRET` - Secret key for JWT signature validation
- `JWT_ISSUER` - Expected JWT issuer
- `JWT_AUDIENCE` - Expected JWT audience

### Authentication Dependency

Created `get_current_user()` FastAPI dependency in `app/core/security.py`:

```python
class CurrentUser(BaseModel):
    """Current authenticated user from JWT."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Extract and validate JWT token from Authorization header."""
```

**Features:**
- Reads Authorization header with Bearer token
- Validates JWT signature, issuer, audience, and expiration
- Extracts user_id from multiple possible claim names:
  - `sub` (priority)
  - `user_id`
  - `userId`
  - `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier`
- Extracts optional email and name claims
- Returns 401 Unauthorized for:
  - Missing token
  - Invalid token
  - Expired token
  - Invalid signature
  - Missing required claims

### FastAPI Security Integration

Added security scheme to `app/main.py`:

```python
from app.core.security import security

app = FastAPI(
    title="StayMatch AI Service",
    lifespan=lifespan,
    security=[{"Bearer": []}],  # Added security scheme
)
```

This enables the "Authorize" button in Swagger UI.

### Endpoint Refactoring

The chat endpoint was refactored to remove user_id from the request body and use JWT authentication.

#### Before/After Endpoint List

| Before | After | Method |
|--------|-------|--------|
| `POST /chat` with `user_id` in body | `POST /chat` with JWT auth | Removed user_id from request body |
| `GET /debug/db-status` | `GET /debug/db-status` | No change (debug endpoint) |

#### Implementation Pattern

**Before:**
```python
class ChatRequest(BaseModel):
    user_id: str
    message: str

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    return await search_service.handle_message(
        session_id=payload.user_id,
        user_id=payload.user_id,
        message=payload.message,
    )
```

**After:**
```python
class ChatRequest(BaseModel):
    message: str

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, current_user: get_current_user = Depends(get_current_user)):
    return await search_service.handle_message(
        session_id=current_user.user_id,
        user_id=current_user.user_id,
        message=payload.message,
    )
```

### Service Layer

**No changes required.** Service layer methods continue to accept `user_id` as a parameter. The router is responsible for extracting the user_id from JWT and passing it to the service. This maintains proper separation of concerns.

### Database Layer

**No changes required.** The database architecture remains unchanged.

## Testing

### Unit Tests

Created comprehensive unit tests in `tests/test_jwt_auth.py`:

- ✅ Valid token validation
- ✅ Token with XML SOAP nameidentifier claim
- ✅ Expired token handling
- ✅ Invalid signature handling
- ✅ Missing user_id claim handling
- ✅ Wrong issuer handling
- ✅ Wrong audience handling
- ✅ Optional claims missing
- ✅ User ID claim priority
- ✅ Fallback to alternative user_id claims

All 10 tests pass.

### Swagger Testing

To test with Swagger UI:

1. Login using .NET Swagger to get JWT token
2. Open AI Service Swagger UI at `http://localhost:8000/docs`
3. Click "Authorize" button
4. Paste JWT token with `Bearer ` prefix: `Bearer eyJ...`
5. Execute `/chat` endpoint
6. User is automatically identified from JWT

### Manual Testing

To test manually with curl:

```bash
# Get JWT from .NET API first
JWT_TOKEN="your-jwt-token-here"

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need help finding accommodation"}'
```

## Error Handling

All authentication errors return `401 Unauthorized`:

- Missing authorization header
- Invalid token
- Expired token
- Invalid signature
- Missing required claim (user_id)
- Wrong issuer
- Wrong audience

## Dependencies

Added to `requirements.txt`:
```
PyJWT==2.8.0
```

## Environment Variables

Add to `.env` file:

```env
# JWT Authentication Configuration
JWT_SECRET=your-jwt-secret-key
JWT_ISSUER=your-jwt-issuer
JWT_AUDIENCE=your-jwt-audience
```

## Security Considerations

- JWT validation is enabled and enforced
- Signature validation is required (unsigned tokens are rejected)
- Expiration validation is enforced
- Issuer and audience validation is enforced
- No authentication bypass mechanisms
- All protected endpoints require valid JWT

## Migration Notes

### For Flutter App

**Before:**
```dart
final response = await http.post(
  Uri.parse('$baseUrl/chat'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'user_id': userId,
    'message': 'Hello',
  }),
);
```

**After:**
```dart
final response = await http.post(
  Uri.parse('$baseUrl/chat'),
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  },
  body: jsonEncode({
    'message': 'Hello',
  }),
);
```

The user_id is no longer needed in the request body - it's extracted from the JWT token.

### For Debug Endpoint

The debug endpoint `/debug/db-status` was NOT refactored and remains without authentication. This is intentional for debugging purposes. Consider adding authentication to this endpoint in production environments.

## Summary

This refactor successfully:
- ✅ Removed user_id from chat request body
- ✅ Implemented JWT authentication with full validation
- ✅ Added Swagger authorization support
- ✅ Maintained database architecture unchanged
- ✅ Maintained service layer unchanged
- ✅ Added comprehensive unit tests
- ✅ Provided clear error handling
- ✅ Documented all changes

The implementation is production-ready and aligns with modern authentication best practices.
