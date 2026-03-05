"""
Main Routes — Home page, AI Chat, PDF Upload/Clear
"""
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from backend.services.chat_service import get_chat_response, chat_logs
from backend.services.pdf_service import extract_pdf_text, get_pdf_text, clear_pdf_text

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    """Render the main website page."""
    return render_template("index.html")


@main_bp.route("/upload", methods=["POST"])
def upload_pdf():
    """Upload and extract text from a PDF file."""
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        file_path = os.path.join(upload_folder, file.filename)
        file.save(file_path)

        text = extract_pdf_text(file_path)
        if not text:
            return jsonify({"error": "Could not extract text from PDF. It may be scanned/image-based."}), 400

        return jsonify({"message": f"PDF '{file.filename}' uploaded and processed successfully."})

    except Exception as e:
        print("Upload Error:", e)
        return jsonify({"error": "Failed to process PDF file."}), 500


@main_bp.route("/chat", methods=["POST"])
def chat():
    """Handle AI chatbot conversation."""
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please enter a message."})

    reply = get_chat_response(user_message, get_pdf_text())
    return jsonify({"reply": reply})


@main_bp.route("/clear-pdf", methods=["POST"])
def clear_pdf():
    """Clear the uploaded PDF context."""
    clear_pdf_text()
    return jsonify({"message": "PDF context cleared."})
