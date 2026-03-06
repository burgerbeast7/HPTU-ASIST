"""
HPTU AI Assistant — WSGI Entry Point
Used by gunicorn: gunicorn app:app
"""
from dotenv import load_dotenv
load_dotenv()

from backend import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))
    is_production = os.getenv("RENDER", "") != ""
    app.run(host="0.0.0.0", port=port, debug=not is_production)