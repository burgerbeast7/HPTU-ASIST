"""
HPTU AI Assistant — Configuration
All application settings and environment variables.
"""
import os
from datetime import timedelta
from werkzeug.security import generate_password_hash


class Config:
    """Central configuration for the Flask application."""

    # Flask core
    SECRET_KEY = os.getenv("SECRET_KEY", "hptu-ai-secret-key-2026-secure")
    UPLOAD_FOLDER = "uploads"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # AI Service
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

    # Admin credentials (hashed)
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD_HASH = generate_password_hash("kunal123")

    # Brute-force protection
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 300  # 5 minutes in seconds

    # Production detection
    IS_PRODUCTION = os.getenv("RENDER", "") != ""

    if IS_PRODUCTION:
        SESSION_COOKIE_SECURE = True
