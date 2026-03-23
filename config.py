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

    # Live search (Google Programmable Search)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "hptu_assistant")

    # Admin credentials (hashed)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD_HASH = generate_password_hash(os.getenv("ADMIN_PASSWORD", "kunal123"))

    # Brute-force protection
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 300  # 5 minutes in seconds

    # Auto-scraper settings
    SCRAPER_INTERVAL_MINUTES = int(os.getenv("SCRAPER_INTERVAL_MINUTES", "30"))
    AUTO_SCRAPE_ENABLED = os.getenv("AUTO_SCRAPE_ENABLED", "true").lower() == "true"

    # Production detection
    IS_PRODUCTION = os.getenv("RENDER", "") != ""

    if IS_PRODUCTION:
        SESSION_COOKIE_SECURE = True
