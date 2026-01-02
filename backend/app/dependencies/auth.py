from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.database import get_db
from app.services.auth_service import AuthService, UserService
from app.schemas.user import UserInDB

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db = Depends(get_db)
) -> Optional[UserInDB]:
    """
    Dependency to get the current user from JWT token.
    Returns None if no token or invalid token (does not raise error).
    Use this for optional authentication.
    """
    if not credentials:
        return None

    token = credentials.credentials
    token_data = AuthService.decode_access_token(token)

    if not token_data:
        return None

    user = UserService.get_user_by_id(db, token_data.user_id)
    return user


async def require_auth(
    current_user: Optional[UserInDB] = Depends(get_current_user)
) -> UserInDB:
    """
    Dependency to require authentication.
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    return current_user


async def require_verified_user(
    current_user: UserInDB = Depends(require_auth)
) -> UserInDB:
    """
    Dependency to require verified email.
    Raises 403 if email not verified.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource."
        )

    return current_user
