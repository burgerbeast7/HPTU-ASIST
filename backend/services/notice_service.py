"""
Notice Service — CRUD operations for notices data files
"""
import json

NOTICES_FILE = "data/notices.json"
HPTU_NOTICES_FILE = "data/hptu_notices.json"


# ─── University Notices (admin-managed) ──────────

def load_notices():
    """Load university notices from JSON file."""
    try:
        with open(NOTICES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_notices(data):
    """Save university notices to JSON file."""
    with open(NOTICES_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─── HPTU Official Notices (scraped) ─────────────

def load_hptu_notices():
    """Load cached HPTU official notices from JSON file."""
    try:
        with open(HPTU_NOTICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_hptu_notices(data):
    """Save HPTU official notices to JSON file."""
    with open(HPTU_NOTICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
