"""
API Routes — JSON endpoints for notices data
"""
from flask import Blueprint, jsonify
from backend.services.notice_service import load_notices, load_hptu_notices

api_bp = Blueprint("api", __name__)


@api_bp.route("/notices")
def get_notices():
    """Return university notices as JSON."""
    return jsonify(load_notices())


@api_bp.route("/hptu-notices")
def get_hptu_notices():
    """Return cached HPTU official notices as JSON."""
    return jsonify(load_hptu_notices())
