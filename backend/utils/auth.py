"""
Auth Utilities — Login decorator for admin route protection
"""
from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    """Decorator to require admin login for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated
