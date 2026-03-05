"""
HPTU AI Assistant — Flask Application Factory
Creates and configures the Flask app with all blueprints registered.
"""
import os
import cohere
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Shared state — accessible across the application
co = None  # Cohere AI client


def create_app():
    """Create and configure the Flask application."""
    global co

    # Resolve paths relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "frontend", "templates"),
        static_folder=os.path.join(project_root, "frontend", "static"),
    )

    # Load configuration
    from config import Config
    app.config.from_object(Config)

    # Fix for running behind Render / any reverse proxy (HTTPS)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Ensure required directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Initialize Cohere AI client
    api_key = app.config.get("COHERE_API_KEY")
    if not api_key:
        print("WARNING: COHERE_API_KEY not set. Chatbot will not work.")
    co = cohere.ClientV2(api_key) if api_key else None

    # ── Register Blueprints ──────────────────────
    from backend.routes.main_routes import main_bp
    from backend.routes.admin_routes import admin_bp
    from backend.routes.api_routes import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
