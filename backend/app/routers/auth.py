from fastapi import APIRouter, HTTPException, Depends, Request, status
from app.schemas.user import (
    UserCreate, UserLogin, Token, UserResponse,
    PasswordResetRequest, PasswordReset, EmailVerificationRequest
)
from app.services.auth_service import AuthService, UserService
from app.services.email_service import EmailService
from app.services.rate_limiter import limiter, LOGIN_RATE_LIMIT, REGISTER_RATE_LIMIT, PASSWORD_RESET_RATE_LIMIT, EMAIL_VERIFY_RATE_LIMIT
from app.dependencies.auth import get_current_user, require_auth
from app.database import get_db
from datetime import timedelta

router = APIRouter()


@router.post("/api/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_RATE_LIMIT)
async def register(
    user_create: UserCreate,
    request: Request,
    db = Depends(get_db)
):
    """
    Register a new user account.

    Rate limited to 3 registrations per hour per IP.
    Sends verification email (non-blocking).
    """
    # Check if user already exists
    existing_user = UserService.get_user_by_email(db, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = UserService.create_user(db, user_create)

    # Send verification email (don't block registration on email failure)
    try:
        verification_token = AuthService.create_verification_token(user.email)
        EmailService.send_verification_email(user.email, verification_token)
    except Exception as e:
        print(f"Failed to send verification email: {e}")

    # Generate access token
    access_token = AuthService.create_access_token(
        data={"user_id": user.user_id, "email": user.email}
    )

    return Token(
        access_token=access_token,
        user=UserService.to_response(user)
    )


@router.post("/api/auth/login", response_model=Token)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    user_login: UserLogin,
    request: Request,
    db = Depends(get_db)
):
    """
    Login with email and password.

    Rate limited to 5 attempts per minute per IP.
    """
    # Get user
    user = UserService.get_user_by_email(db, user_login.email)

    # Check user exists and password is correct
    if not user or not AuthService.verify_password(user_login.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Update last login
    UserService.update_last_login(db, user.user_id)

    # Generate access token
    access_token = AuthService.create_access_token(
        data={"user_id": user.user_id, "email": user.email}
    )

    return Token(
        access_token=access_token,
        user=UserService.to_response(user)
    )


@router.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user = Depends(require_auth)):
    """
    Get current authenticated user.

    Requires valid JWT token.
    """
    return UserService.to_response(current_user)


@router.post("/api/auth/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    verification: EmailVerificationRequest,
    db = Depends(get_db)
):
    """
    Verify email address with token from email.
    """
    # Verify token
    email = AuthService.verify_token(verification.token, "email_verification")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Mark email as verified
    success = UserService.verify_email(db, email)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "Email verified successfully"}


@router.post("/api/auth/resend-verification", status_code=status.HTTP_200_OK)
@limiter.limit(EMAIL_VERIFY_RATE_LIMIT)
async def resend_verification(
    request: Request,
    current_user = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Resend verification email.

    Rate limited to 5 per hour per IP.
    """
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Send verification email
    verification_token = AuthService.create_verification_token(current_user.email)
    success = EmailService.send_verification_email(current_user.email, verification_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

    return {"message": "Verification email sent"}


@router.post("/api/auth/request-password-reset", status_code=status.HTTP_200_OK)
@limiter.limit(PASSWORD_RESET_RATE_LIMIT)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    request: Request,
    db = Depends(get_db)
):
    """
    Request password reset email.

    Rate limited to 3 per hour per IP.
    Always returns success to prevent email enumeration.
    """
    # Get user (but don't reveal if email exists)
    user = UserService.get_user_by_email(db, reset_request.email)

    if user:
        # Send password reset email
        reset_token = AuthService.create_password_reset_token(user.email)
        EmailService.send_password_reset_email(user.email, reset_token)

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/api/auth/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    password_reset: PasswordReset,
    db = Depends(get_db)
):
    """
    Reset password with token from email.
    """
    # Verify token
    email = AuthService.verify_token(password_reset.token, "password_reset")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password
    success = UserService.update_password(db, email, password_reset.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "Password reset successfully"}
