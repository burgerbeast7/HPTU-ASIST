"""
API Routes — JSON endpoints for notices, syllabus, fees, scraper status
"""
from flask import Blueprint, jsonify
from backend.services.notice_service import (
    load_notices, load_hptu_notices, load_syllabus,
    load_fees, load_scraped_pdfs, load_scraper_status, load_pyq
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/notices")
def get_notices():
    """Return university notices as JSON."""
    return jsonify(load_notices())


@api_bp.route("/hptu-notices")
def get_hptu_notices():
    """Return HPTU official notices as JSON."""
    return jsonify(load_hptu_notices())


@api_bp.route("/syllabus")
def get_syllabus():
    """Return syllabus data as JSON."""
    return jsonify(load_syllabus())


@api_bp.route("/fees")
def get_fees():
    """Return fees data as JSON."""
    return jsonify(load_fees())


@api_bp.route("/scraper-status")
def get_scraper_status():
    """Return current scraper status."""
    return jsonify(load_scraper_status())


@api_bp.route("/scraped-pdfs")
def get_scraped_pdfs():
    """Return list of scraped PDFs (without full text, for UI)."""
    pdfs = load_scraped_pdfs()
    # Return summary only, not full text
    summary = []
    for p in pdfs:
        summary.append({
            "title": p.get("title", ""),
            "url": p.get("url", ""),
            "category": p.get("category", ""),
            "text_preview": p.get("text", "")[:200] + "..." if p.get("text") else "",
        })
    return jsonify(summary)


@api_bp.route("/pyq")
def get_pyq():
    """Return all scraped PYQ (Previous Year Questions) as JSON."""
    return jsonify(load_pyq())


@api_bp.route("/pyq/search")
def search_pyq_api():
    """Search PYQ papers by keyword."""
    from flask import request
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Please provide a search query using ?q=keyword"}), 400
    from backend.services.pyq_service import search_pyq
    results = search_pyq(query)
    return jsonify(results)
