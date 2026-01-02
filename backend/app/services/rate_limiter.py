from slowapi import Limiter
from slowapi.util import get_remote_address
import os

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
)

# Rate limit decorators for different operations
# Login: 5 attempts per minute per IP
LOGIN_RATE_LIMIT = "5/minute"

# Registration: 3 per hour per IP
REGISTER_RATE_LIMIT = "3/hour"

# Password reset request: 3 per hour per IP
PASSWORD_RESET_RATE_LIMIT = "3/hour"

# Email verification resend: 5 per hour per IP
EMAIL_VERIFY_RATE_LIMIT = "5/hour"
