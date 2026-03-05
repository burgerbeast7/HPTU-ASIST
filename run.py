"""
HPTU AI Assistant — Application Entry Point
Run this file to start the Flask development server.

Usage:
    python run.py
"""
from dotenv import load_dotenv
load_dotenv()

import os
from backend import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    is_production = os.getenv("RENDER", "") != ""
    app.run(host="0.0.0.0", port=port, debug=not is_production)
