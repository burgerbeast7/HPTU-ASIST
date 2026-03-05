"""
PDF Service — PDF text extraction and in-memory storage
"""
from pypdf import PdfReader

# In-memory storage for the currently loaded PDF text
_pdf_text_storage = ""


def extract_pdf_text(file_path):
    """
    Extract text from a PDF file and store it in memory.
    Returns the extracted text, or None if no text could be extracted.
    """
    global _pdf_text_storage

    reader = PdfReader(file_path)
    extracted_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"

    if not extracted_text.strip():
        return None

    _pdf_text_storage = extracted_text
    return extracted_text


def get_pdf_text():
    """Return the currently stored PDF text."""
    return _pdf_text_storage


def clear_pdf_text():
    """Clear the stored PDF text from memory."""
    global _pdf_text_storage
    _pdf_text_storage = ""
