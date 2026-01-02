from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import os

from app.schemas.user import UserCreate, UserInDB, UserResponse, TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_verification_token(email: str) -> str:
        """Create a token for email verification (expires in 24h)"""
        data = {
            "email": email,
            "type": "email_verification"
        }
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        data.update({"exp": expire})
        return jwt.encode(data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create a token for password reset (expires in 1h)"""
        data = {
            "email": email,
            "type": "password_reset"
        }
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        data.update({"exp": expire})
        return jwt.encode(data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str, expected_type: str) -> Optional[str]:
        """
        Verify a JWT token and return the email if valid.
        Returns None if invalid or expired.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            email: str = payload.get("email")
            token_type: str = payload.get("type")

            if email is None or token_type != expected_type:
                return None

            return email
        except JWTError:
            return None

    @staticmethod
    def decode_access_token(token: str) -> Optional[TokenData]:
        """Decode and verify an access token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")

            if user_id is None or email is None:
                return None

            return TokenData(user_id=user_id, email=email)
        except JWTError:
            return None


class UserService:
    """Service for user CRUD operations"""

    @staticmethod
    def create_user(db, user_create: UserCreate) -> UserInDB:
        """Create a new user in the database"""
        now = datetime.now(timezone.utc)

        user = UserInDB(
            user_id=str(uuid.uuid4()),
            email=user_create.email.lower(),
            hashed_password=AuthService.hash_password(user_create.password),
            is_verified=False,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        user_doc = user.model_dump()
        db.users.insert_one(user_doc)

        return user

    @staticmethod
    def get_user_by_email(db, email: str) -> Optional[UserInDB]:
        """Get a user by email"""
        user_doc = db.users.find_one({"email": email.lower()})
        if not user_doc:
            return None

        user_doc.pop("_id", None)
        return UserInDB(**user_doc)

    @staticmethod
    def get_user_by_id(db, user_id: str) -> Optional[UserInDB]:
        """Get a user by ID"""
        user_doc = db.users.find_one({"user_id": user_id})
        if not user_doc:
            return None

        user_doc.pop("_id", None)
        return UserInDB(**user_doc)

    @staticmethod
    def update_user(db, user_id: str, updates: dict) -> bool:
        """Update a user's fields"""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = db.users.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    @staticmethod
    def verify_email(db, email: str) -> bool:
        """Mark a user's email as verified"""
        return UserService.update_user_by_email(db, email, {"is_verified": True})

    @staticmethod
    def update_user_by_email(db, email: str, updates: dict) -> bool:
        """Update a user by email"""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = db.users.update_one(
            {"email": email.lower()},
            {"$set": updates}
        )
        return result.modified_count > 0

    @staticmethod
    def update_password(db, email: str, new_password: str) -> bool:
        """Update a user's password"""
        hashed = AuthService.hash_password(new_password)
        return UserService.update_user_by_email(db, email, {"hashed_password": hashed})

    @staticmethod
    def update_last_login(db, user_id: str) -> bool:
        """Update user's last login timestamp"""
        return UserService.update_user(db, user_id, {"last_login": datetime.now(timezone.utc)})

    @staticmethod
    def to_response(user: UserInDB) -> UserResponse:
        """Convert UserInDB to UserResponse (remove sensitive fields)"""
        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            is_verified=user.is_verified,
            is_active=user.is_active,
            created_at=user.created_at
        )
