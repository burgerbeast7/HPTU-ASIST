"""
Notice Service — MongoDB-backed CRUD operations for all data types
Handles: notices, hptu_notices, syllabus, fees, scraped_pdfs, chat_logs
Falls back to JSON files if MongoDB is unavailable.
"""
import json
import os
from datetime import datetime

NOTICES_FILE = "data/notices.json"
HPTU_NOTICES_FILE = "data/hptu_notices.json"


def _get_collection(name):
    """Lazy import to avoid circular imports."""
    from backend.db import get_collection
    return get_collection(name)


# ─── University Notices (admin-managed) ──────────

def load_notices():
    col = _get_collection("notices")
    if col is not None:
        try:
            notices = {}
            for doc in col.find({}, {"_id": 0}):
                nid = doc.get("notice_id", "")
                notices[nid] = {
                    "title": doc.get("title", ""),
                    "date": doc.get("date", ""),
                    "description": doc.get("description", ""),
                }
            if notices:
                return notices
        except Exception as e:
            print(f"MongoDB load_notices error: {e}")
    try:
        with open(NOTICES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_notices(data):
    col = _get_collection("notices")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                docs = []
                for nid, notice in data.items():
                    docs.append({
                        "notice_id": nid,
                        "title": notice.get("title", ""),
                        "date": notice.get("date", ""),
                        "description": notice.get("description", ""),
                        "updated_at": datetime.utcnow(),
                    })
                col.insert_many(docs)
        except Exception as e:
            print(f"MongoDB save_notices error: {e}")
    try:
        with open(NOTICES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ─── HPTU Official Notices (scraped) ─────────────

def load_hptu_notices():
    col = _get_collection("hptu_notices")
    if col is not None:
        try:
            notices = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                notices.append({
                    "title": doc.get("title", ""),
                    "date": doc.get("date", ""),
                    "last_date": doc.get("last_date", ""),
                    "link": doc.get("link", ""),
                    "source": doc.get("source", "hptu_official"),
                    "category": doc.get("category", "general"),
                    "pdf_text": doc.get("pdf_text", ""),
                })
            if notices:
                return notices
        except Exception as e:
            print(f"MongoDB load_hptu_notices error: {e}")
    try:
        with open(HPTU_NOTICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_hptu_notices(data):
    col = _get_collection("hptu_notices")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                now = datetime.utcnow()
                docs = []
                for notice in data:
                    doc = {
                        "title": notice.get("title", ""),
                        "date": notice.get("date", ""),
                        "last_date": notice.get("last_date", ""),
                        "link": notice.get("link", ""),
                        "source": notice.get("source", "hptu_official"),
                        "category": notice.get("category", "general"),
                        "pdf_text": notice.get("pdf_text", ""),
                        "scraped_at": now,
                    }
                    docs.append(doc)
                col.insert_many(docs)
        except Exception as e:
            print(f"MongoDB save_hptu_notices error: {e}")
    try:
        with open(HPTU_NOTICES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ─── Syllabus Data ───────────────────────────────

def load_syllabus():
    col = _get_collection("syllabus")
    if col is not None:
        try:
            items = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                items.append(doc)
            return items
        except Exception as e:
            print(f"MongoDB load_syllabus error: {e}")
    return []


def save_syllabus(data):
    col = _get_collection("syllabus")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                now = datetime.utcnow()
                for item in data:
                    item["scraped_at"] = now
                col.insert_many(data)
        except Exception as e:
            print(f"MongoDB save_syllabus error: {e}")


# ─── Fees Data ───────────────────────────────────

def load_fees():
    col = _get_collection("fees")
    if col is not None:
        try:
            items = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                items.append(doc)
            return items
        except Exception as e:
            print(f"MongoDB load_fees error: {e}")
    return []


def save_fees(data):
    col = _get_collection("fees")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                now = datetime.utcnow()
                for item in data:
                    item["scraped_at"] = now
                col.insert_many(data)
        except Exception as e:
            print(f"MongoDB save_fees error: {e}")


# ─── Scraped PDF Content ─────────────────────────

def load_scraped_pdfs():
    col = _get_collection("scraped_pdfs")
    if col is not None:
        try:
            pdfs = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                pdfs.append(doc)
            return pdfs
        except Exception as e:
            print(f"MongoDB load_scraped_pdfs error: {e}")
    return []


def save_scraped_pdf(pdf_data):
    col = _get_collection("scraped_pdfs")
    if col is not None:
        try:
            pdf_data["scraped_at"] = datetime.utcnow()
            col.update_one(
                {"url": pdf_data.get("url", "")},
                {"$set": pdf_data},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB save_scraped_pdf error: {e}")


# ─── Documents / Resources ───────────────────────

def load_documents():
    """Load all scraped documents/resources from MongoDB."""
    col = _get_collection("documents")
    if col is not None:
        try:
            docs = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                docs.append(doc)
            return docs
        except Exception as e:
            print(f"MongoDB load_documents error: {e}")
    return []


def save_documents(data):
    """Save scraped documents/resources to MongoDB (replace all)."""
    col = _get_collection("documents")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                now = datetime.utcnow()
                for item in data:
                    item["scraped_at"] = now
                col.insert_many(data)
        except Exception as e:
            print(f"MongoDB save_documents error: {e}")


# ─── PYQ (Previous Year Questions) ───────────────

def load_pyq():
    """Load all scraped PYQ papers from MongoDB."""
    col = _get_collection("pyq")
    if col is not None:
        try:
            items = []
            for doc in col.find({}, {"_id": 0}).sort("scraped_at", -1):
                items.append(doc)
            return items
        except Exception as e:
            print(f"MongoDB load_pyq error: {e}")
    return []


def save_pyq(data):
    """Save scraped PYQ papers to MongoDB (replace all)."""
    col = _get_collection("pyq")
    if col is not None:
        try:
            col.delete_many({})
            if data:
                now = datetime.utcnow()
                for item in data:
                    item["scraped_at"] = now
                col.insert_many(data)
        except Exception as e:
            print(f"MongoDB save_pyq error: {e}")


# ─── Chat Logs (persistent in MongoDB) ───────────

def save_chat_log(user_msg, bot_reply):
    col = _get_collection("chat_logs")
    if col is not None:
        try:
            col.insert_one({
                "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "user": user_msg[:200],
                "bot": bot_reply[:300],
                "created_at": datetime.utcnow(),
            })
            count = col.count_documents({})
            if count > 500:
                oldest = col.find().sort("created_at", 1).limit(count - 500)
                ids = [doc["_id"] for doc in oldest]
                col.delete_many({"_id": {"$in": ids}})
        except Exception as e:
            print(f"MongoDB save_chat_log error: {e}")


def load_chat_logs(limit=50):
    col = _get_collection("chat_logs")
    if col is not None:
        try:
            logs = []
            for doc in col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit):
                logs.append({
                    "time": doc.get("time", ""),
                    "user": doc.get("user", ""),
                    "bot": doc.get("bot", ""),
                })
            return list(reversed(logs))
        except Exception as e:
            print(f"MongoDB load_chat_logs error: {e}")
    return []


def clear_chat_logs_db():
    col = _get_collection("chat_logs")
    if col is not None:
        try:
            col.delete_many({})
        except Exception as e:
            print(f"MongoDB clear_chat_logs error: {e}")


# ─── Scraper Status ──────────────────────────────

def save_scraper_status(status_data):
    col = _get_collection("scraper_status")
    if col is not None:
        try:
            status_data["updated_at"] = datetime.utcnow()
            status_data["key"] = "last_run"
            col.update_one(
                {"key": "last_run"},
                {"$set": status_data},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB save_scraper_status error: {e}")


def load_scraper_status():
    col = _get_collection("scraper_status")
    if col is not None:
        try:
            doc = col.find_one({"key": "last_run"}, {"_id": 0})
            if doc:
                return doc
        except Exception as e:
            print(f"MongoDB load_scraper_status error: {e}")
    return {
        "status": "never_run",
        "last_run": "Never",
        "notices_count": 0,
        "pdfs_scanned": 0,
        "syllabus_count": 0,
        "fees_count": 0,
    }
