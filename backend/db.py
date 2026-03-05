"""
Database Module — MongoDB connection and collection accessors
Uses MongoDB Atlas (or local MongoDB) for persistent storage.
"""
import os
from pymongo import MongoClient

_client = None
_db = None


def get_db():
    """Get the MongoDB database instance. Creates connection on first call."""
    global _client, _db
    if _db is not None:
        return _db

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGODB_DB_NAME", "hptu_assistant")

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        _client.admin.command("ping")
        _db = _client[db_name]
        print(f"✅ MongoDB connected: {db_name}")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("   Using fallback in-memory storage.")
        _db = None

    return _db


def get_collection(name):
    """Get a MongoDB collection by name. Returns None if DB is unavailable."""
    db = get_db()
    if db is not None:
        return db[name]
    return None


def close_db():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
