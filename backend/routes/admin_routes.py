"""
Admin Routes — Dashboard, Authentication, Data Management, Scraper Controls
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app
from werkzeug.security import check_password_hash

from backend.services.notice_service import (
    load_notices, save_notices, load_hptu_notices, save_hptu_notices,
    load_syllabus, load_fees, load_scraped_pdfs, load_scraper_status,
    load_chat_logs
)
from backend.services.scraper_service import scrape_hptu_notices, run_full_scrape
from backend.services.chat_service import chat_logs
from backend.utils.auth import login_required

admin_bp = Blueprint("admin", __name__)

# Brute-force protection state
failed_login_attempts = {}


@admin_bp.before_request
def protect_admin():
    """Protect all admin routes."""
    if request.endpoint in ("admin.login", "admin.logout"):
        return None
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))


# ─── Authentication ──────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))

    error = None
    if request.method == "POST":
        client_ip = request.remote_addr
        max_attempts = current_app.config["MAX_LOGIN_ATTEMPTS"]
        lockout_time = current_app.config["LOCKOUT_TIME"]

        if client_ip in failed_login_attempts:
            attempts, last_time = failed_login_attempts[client_ip]
            if attempts >= max_attempts:
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < lockout_time:
                    remaining = int((lockout_time - elapsed) / 60) + 1
                    error = f"Too many failed attempts. Try again in {remaining} minute(s)."
                    return render_template("admin/login.html", error=error)
                else:
                    del failed_login_attempts[client_ip]

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if (username == current_app.config["ADMIN_USERNAME"]
                and check_password_hash(current_app.config["ADMIN_PASSWORD_HASH"], password)):
            session["admin_logged_in"] = True
            session.permanent = True
            failed_login_attempts.pop(client_ip, None)
            return redirect(url_for("admin.dashboard"))
        else:
            if client_ip in failed_login_attempts:
                count, _ = failed_login_attempts[client_ip]
                failed_login_attempts[client_ip] = (count + 1, datetime.now())
            else:
                failed_login_attempts[client_ip] = (1, datetime.now())
            error = "Invalid username or password."

    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


# ─── Dashboard ───────────────────────────────────

@admin_bp.route("/")
@login_required
def dashboard():
    notices = load_notices()
    hptu_notices = load_hptu_notices()
    syllabus = load_syllabus()
    fees = load_fees()
    scraped_pdfs = load_scraped_pdfs()
    scraper_status = load_scraper_status()
    db_chat_logs = load_chat_logs(50)

    # Get uploaded PDF files
    uploaded_files = []
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, f)
            if os.path.isfile(fpath):
                size_kb = round(os.path.getsize(fpath) / 1024, 1)
                mod_time = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
                uploaded_files.append({"name": f, "size": size_kb, "date": mod_time})

    from backend import co
    stats = {
        "total_notices": len(notices),
        "total_uploads": len(uploaded_files),
        "total_chats": len(db_chat_logs) or len(chat_logs),
        "ai_status": "Connected" if co else "Not Configured",
        "hptu_notices": len(hptu_notices),
        "syllabus_count": len(syllabus),
        "fees_count": len(fees),
        "pdfs_scanned": len(scraped_pdfs),
    }

    # Use DB chat logs if available, otherwise in-memory
    display_logs = db_chat_logs if db_chat_logs else chat_logs[-20:]

    return render_template("admin/dashboard.html",
                           notices=notices,
                           uploaded_files=uploaded_files,
                           chat_logs=display_logs,
                           hptu_notices=hptu_notices,
                           syllabus=syllabus,
                           fees=fees,
                           scraped_pdfs=scraped_pdfs,
                           scraper_status=scraper_status,
                           stats=stats)


# ─── Notice Management ───────────────────────────

@admin_bp.route("/notice/add", methods=["POST"])
@login_required
def add_notice():
    notices = load_notices()
    notice_id = "notice_" + uuid.uuid4().hex[:8]
    notices[notice_id] = {
        "title": request.form.get("title", "").strip(),
        "date": request.form.get("date", "").strip(),
        "description": request.form.get("description", "").strip(),
    }
    save_notices(notices)
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/notice/delete/<notice_id>", methods=["POST"])
@login_required
def delete_notice(notice_id):
    notices = load_notices()
    notices.pop(notice_id, None)
    save_notices(notices)
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/notice/edit/<notice_id>", methods=["POST"])
@login_required
def edit_notice(notice_id):
    notices = load_notices()
    if notice_id in notices:
        title = request.form.get("title", "").strip()
        date = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()
        if title:
            notices[notice_id]["title"] = title
        if date:
            notices[notice_id]["date"] = date
        if description:
            notices[notice_id]["description"] = description
        save_notices(notices)
    return redirect(url_for("admin.dashboard"))


# ─── PDF Upload Management ───────────────────────

@admin_bp.route("/upload", methods=["POST"])
@login_required
def upload_pdf():
    if "pdf" not in request.files:
        return redirect(url_for("admin.dashboard"))
    file = request.files["pdf"]
    if file.filename and file.filename.lower().endswith(".pdf"):
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/upload/delete/<filename>", methods=["POST"])
@login_required
def delete_upload(filename):
    fpath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(fpath):
        os.remove(fpath)
    return redirect(url_for("admin.dashboard"))


# ─── Chat Log Management ─────────────────────────

@admin_bp.route("/clear-chats", methods=["POST"])
@login_required
def clear_chats():
    from backend.services.chat_service import clear_chat_logs
    clear_chat_logs()
    return redirect(url_for("admin.dashboard"))


# ─── HPTU Data Scraper Controls ──────────────────

@admin_bp.route("/fetch-hptu-notices", methods=["POST"])
@login_required
def fetch_hptu_notices():
    """Quick fetch — just notices from HPTU."""
    notices = scrape_hptu_notices()
    if notices:
        save_hptu_notices(notices)
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/run-full-scrape", methods=["POST"])
@login_required
def trigger_full_scrape():
    """Run full comprehensive scrape (notices + PDFs + syllabus + fees)."""
    status = run_full_scrape()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clear-hptu-notices", methods=["POST"])
@login_required
def clear_hptu_notices():
    save_hptu_notices([])
    return redirect(url_for("admin.dashboard"))
