from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cohere
from dotenv import load_dotenv
import os
import json
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pypdf import PdfReader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
# Fix for running behind Render / any reverse proxy (HTTPS)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config["UPLOAD_FOLDER"] = "uploads"
app.secret_key = os.getenv("SECRET_KEY", "hptu-ai-secret-key-2026-secure")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# Session cookie configuration — works on both HTTP (local) and HTTPS (Render)
IS_PRODUCTION = os.getenv("RENDER", "") != ""
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if IS_PRODUCTION:
    app.config["SESSION_COOKIE_SECURE"] = True

# Admin credentials — secured with password hashing
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("kunal123")

# Brute force protection
failed_login_attempts = {}
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minutes in seconds

# Ensure directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("data", exist_ok=True)

# Initialize Cohere client
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    print("WARNING: COHERE_API_KEY not set. Chatbot will not work.")
co = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None

pdf_text_storage = ""  # Temporary storage for extracted PDF text
chat_logs = []  # Store recent chat logs for admin dashboard

# HPTU Knowledge base for the AI assistant
HPTU_SYSTEM_PROMPT = """You are the official AI Assistant for Himachal Pradesh Technical University (HPTU), Hamirpur.
You help students, faculty, and visitors with university-related queries.

KEY FACTS ABOUT HPTU:
- Full Name: Himachal Pradesh Technical University (HPTU)
- Location: Hamirpur, Himachal Pradesh, India
- Established: 2010 under HP Technical University Act
- Type: State Technical University
- Website: www.himtu.ac.in
- Chancellor: Governor of Himachal Pradesh
- Affiliation: Affiliates engineering, pharmacy, management, and other technical colleges across Himachal Pradesh

ACADEMICS:
- Offers B.Tech, M.Tech, BBA, MBA, BCA, MCA, B.Pharmacy, M.Pharmacy, Diploma programs
- Branches include: CSE, ECE, EE, ME, CE, IT, and more
- Academic calendar typically follows semester system
- Exams are conducted by the university for all affiliated colleges

ADMISSIONS:
- B.Tech admissions through HPCET (HP Common Entrance Test) / JEE Main
- MBA admissions through HPCET / MAT / CMAT
- M.Tech through GATE / HPCET
- Lateral entry available for diploma holders

EXAMINATIONS:
- University conducts end-semester exams
- Results available on official website: www.himtu.ac.in
- Students can apply for re-evaluation
- Exam date sheets published on the website

IMPORTANT CONTACTS:
- University Address: Gandhi Chowk, Hamirpur, HP - 177001
- Phone: 01972-223504
- Email: info@himtu.ac.in

RESPONSE GUIDELINES:
- Be helpful, accurate, and professional
- If you don't know something specific, suggest checking the official website www.himtu.ac.in
- Format responses clearly with bullet points when listing information
- Keep responses concise but informative
- Always be polite and supportive to students"""


@app.route("/")
def home():
    return render_template("index.html")


# Load notices data
def load_notices():
    try:
        with open("data/notices.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


@app.route("/api/notices")
def get_notices():
    return jsonify(load_notices())


# ─── HPTU Website Scraper ─────────────────────
HPTU_NOTICES_FILE = "data/hptu_notices.json"


def load_hptu_notices():
    try:
        with open(HPTU_NOTICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_hptu_notices(data):
    with open(HPTU_NOTICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def scrape_hptu_notices():
    """Scrape latest notifications from the official HPTU website."""
    notices = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://www.himtu.ac.in/notice-board"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # The notice board page uses a table with rows
        rows = soup.select("table tbody tr")
        if not rows:
            # Fallback: try finding table rows without tbody
            rows = soup.select("table tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            title = cells[0].get_text(strip=True)
            if not title:
                continue

            date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            last_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""

            # Find document download link
            doc_link = ""
            for cell in cells:
                link_tag = cell.find("a", href=True)
                if link_tag:
                    href = link_tag["href"]
                    if href.startswith("/"):
                        href = "https://www.himtu.ac.in" + href
                    if href.endswith(".pdf") or "default/files" in href or href.startswith("http"):
                        doc_link = href
                        break

            notices.append({
                "title": title,
                "date": date,
                "last_date": last_date,
                "link": doc_link,
                "source": "hptu_official"
            })

        # Also try scraping from the home page "What's New" ticker
        if not notices:
            home_resp = requests.get("https://www.himtu.ac.in/", headers=headers, timeout=15)
            home_soup = BeautifulSoup(home_resp.text, "html.parser")
            # Look for notification links in the marquee/ticker area
            ticker_links = home_soup.select('.marquee-content a, .whats-new a, [class*="ticker"] a, [class*="notification"] a')
            for link in ticker_links[:20]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if title and len(title) > 10:
                    if href.startswith("/"):
                        href = "https://www.himtu.ac.in" + href
                    notices.append({
                        "title": title,
                        "date": "",
                        "last_date": "",
                        "link": href,
                        "source": "hptu_official"
                    })

    except Exception as e:
        print(f"HPTU Scrape Error: {e}")

    return notices


@app.route("/api/hptu-notices")
def get_hptu_notices():
    """Return cached HPTU notices."""
    return jsonify(load_hptu_notices())


# ============================================
#          ADMIN PANEL ROUTES
# ============================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def save_notices(data):
    with open("data/notices.json", "w") as f:
        json.dump(data, f, indent=2)


@app.route("/admin/fetch-hptu-notices", methods=["POST"])
@login_required
def admin_fetch_hptu_notices():
    """Scrape fresh notices from HPTU website and save."""
    notices = scrape_hptu_notices()
    if notices:
        save_hptu_notices(notices)
        return redirect(url_for("admin_dashboard"))
    else:
        # If scraping returned nothing, keep existing data
        return redirect(url_for("admin_dashboard"))


@app.route("/admin/clear-hptu-notices", methods=["POST"])
@login_required
def admin_clear_hptu_notices():
    """Clear cached HPTU notices."""
    save_hptu_notices([])
    return redirect(url_for("admin_dashboard"))


# Upload PDF
@app.route("/upload", methods=["POST"])
def upload_pdf():
    global pdf_text_storage

    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    try:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        reader = PdfReader(file_path)
        extracted_text = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        if not extracted_text.strip():
            return jsonify({"error": "Could not extract text from PDF. It may be scanned/image-based."}), 400

        pdf_text_storage = extracted_text
        return jsonify({"message": f"PDF '{file.filename}' uploaded and processed successfully."})

    except Exception as e:
        print("Upload Error:", e)
        return jsonify({"error": "Failed to process PDF file."}), 500


# Chat Route
@app.route("/chat", methods=["POST"])
def chat():
    global pdf_text_storage

    if not co:
        return jsonify({"reply": "AI service is not configured. Please set the COHERE_API_KEY."})

    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please enter a message."})

    try:
        messages = []

        if pdf_text_storage:
            system_prompt = HPTU_SYSTEM_PROMPT + f"""

A PDF document has been uploaded. Use its content to answer questions when relevant.

PDF Content:
{pdf_text_storage[:15000]}
"""
        else:
            system_prompt = HPTU_SYSTEM_PROMPT

        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = co.chat(
            model="command-a-03-2025",
            messages=messages,
        )

        reply = response.message.content[0].text

    except Exception as e:
        print("Chat Error:", e)
        reply = "I'm sorry, I'm having trouble connecting to the AI service right now. Please try again in a moment."

    # Log the chat for admin dashboard
    chat_logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_message[:100],
        "bot": reply[:150],
    })
    # Keep only last 50 logs in memory
    if len(chat_logs) > 50:
        chat_logs.pop(0)

    return jsonify({"reply": reply})


# Clear PDF context
@app.route("/clear-pdf", methods=["POST"])
def clear_pdf():
    global pdf_text_storage
    pdf_text_storage = ""
    return jsonify({"message": "PDF context cleared."})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        client_ip = request.remote_addr

        # Check if locked out
        if client_ip in failed_login_attempts:
            attempts, last_time = failed_login_attempts[client_ip]
            if attempts >= MAX_ATTEMPTS:
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < LOCKOUT_TIME:
                    remaining = int((LOCKOUT_TIME - elapsed) / 60) + 1
                    error = f"Too many failed attempts. Try again in {remaining} minute(s)."
                    return render_template("admin_login.html", error=error)
                else:
                    del failed_login_attempts[client_ip]

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            session.permanent = True
            # Clear failed attempts on success
            failed_login_attempts.pop(client_ip, None)
            return redirect(url_for("admin_dashboard"))
        else:
            # Track failed attempt
            if client_ip in failed_login_attempts:
                count, _ = failed_login_attempts[client_ip]
                failed_login_attempts[client_ip] = (count + 1, datetime.now())
            else:
                failed_login_attempts[client_ip] = (1, datetime.now())
            error = "Invalid username or password."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    notices = load_notices()
    # Get uploaded PDFs
    uploaded_files = []
    upload_dir = app.config["UPLOAD_FOLDER"]
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, f)
            if os.path.isfile(fpath):
                size_kb = round(os.path.getsize(fpath) / 1024, 1)
                mod_time = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
                uploaded_files.append({"name": f, "size": size_kb, "date": mod_time})

    hptu_notices = load_hptu_notices()

    stats = {
        "total_notices": len(notices),
        "total_uploads": len(uploaded_files),
        "total_chats": len(chat_logs),
        "ai_status": "Connected" if co else "Not Configured",
        "hptu_notices": len(hptu_notices),
    }

    return render_template("admin_dashboard.html",
                           notices=notices,
                           uploaded_files=uploaded_files,
                           chat_logs=chat_logs[-20:],
                           hptu_notices=hptu_notices,
                           stats=stats)


@app.route("/admin/notice/add", methods=["POST"])
@login_required
def admin_add_notice():
    notices = load_notices()
    notice_id = "notice_" + uuid.uuid4().hex[:8]
    notices[notice_id] = {
        "title": request.form.get("title", "").strip(),
        "date": request.form.get("date", "").strip(),
        "description": request.form.get("description", "").strip(),
    }
    save_notices(notices)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/notice/delete/<notice_id>", methods=["POST"])
@login_required
def admin_delete_notice(notice_id):
    notices = load_notices()
    notices.pop(notice_id, None)
    save_notices(notices)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/upload/delete/<filename>", methods=["POST"])
@login_required
def admin_delete_upload(filename):
    fpath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(fpath):
        os.remove(fpath)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/notice/edit/<notice_id>", methods=["POST"])
@login_required
def admin_edit_notice(notice_id):
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
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload_pdf():
    if "pdf" not in request.files:
        return redirect(url_for("admin_dashboard"))
    file = request.files["pdf"]
    if file.filename and file.filename.lower().endswith(".pdf"):
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/clear-chats", methods=["POST"])
@login_required
def admin_clear_chats():
    global chat_logs
    chat_logs = []
    return redirect(url_for("admin_dashboard"))


# Block anyone trying to access /admin paths without proper auth
@app.before_request
def protect_admin_routes():
    if request.path.startswith("/admin"):
        # Allow access to login and logout without auth
        if request.endpoint in ("admin_login", "admin_logout", "static"):
            return None
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=not IS_PRODUCTION)