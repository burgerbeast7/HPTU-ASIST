"""
HPTU AI Assistant — Flask Application Factory
Creates and configures the Flask app with all blueprints and scheduler.
"""
import os
import atexit
import cohere
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Shared state — accessible across the application
co = None  # Cohere AI client
scheduler = None  # APScheduler instance


def create_app():
    """Create and configure the Flask application."""
    global co, scheduler

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

    # Initialize MongoDB connection
    from backend.db import get_db
    get_db()

    # Initialize Cohere AI client
    api_key = app.config.get("COHERE_API_KEY")
    if not api_key:
        print("⚠️  WARNING: COHERE_API_KEY not set. Chatbot will not work.")
    co = cohere.ClientV2(api_key) if api_key else None

    # ── Register Blueprints ──────────────────────
    from backend.routes.main_routes import main_bp
    from backend.routes.admin_routes import admin_bp
    from backend.routes.api_routes import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # ── Start Background Scheduler ───────────────
    if app.config.get("AUTO_SCRAPE_ENABLED", True):
        _start_scheduler(app)

    return app


def _start_scheduler(app):
    """Start APScheduler for auto-scraping HPTU data."""
    global scheduler

    # Prevent double scheduler in debug reload
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and app.debug:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        interval = app.config.get("SCRAPER_INTERVAL_MINUTES", 30)
        scheduler = BackgroundScheduler(daemon=True)

        def scheduled_scrape():
            """Run the comprehensive scraper in app context."""
            with app.app_context():
                from backend.services.scraper_service import run_full_scrape
                print("🔄 Auto-scraper running...")
                run_full_scrape()
                print("✅ Auto-scrape complete.")

        scheduler.add_job(
            scheduled_scrape,
            "interval",
            minutes=interval,
            id="hptu_auto_scraper",
            replace_existing=True,
        )
        scheduler.start()
        print(f"⏰ Auto-scraper enabled: runs every {interval} minutes")

        atexit.register(lambda: scheduler.shutdown(wait=False))

        # Run initial scrape after 10 seconds
        from apscheduler.triggers.date import DateTrigger
        from datetime import datetime, timedelta
        scheduler.add_job(
            scheduled_scrape,
            DateTrigger(run_date=datetime.now() + timedelta(seconds=10)),
            id="initial_scrape",
            replace_existing=True,
        )

    except Exception as e:
        print(f"⚠️  Scheduler error: {e}")
