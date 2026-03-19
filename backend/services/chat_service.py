"""
Chat Service — Fast AI chatbot with smart context loading
Only loads relevant data based on user query. Caches context. Uses faster model.
"""
import time
import re
from datetime import datetime

# In-memory chat logs
chat_logs = []

# ── In-memory cache to avoid repeated MongoDB reads ──
_context_cache = {
    "notices": None,
    "documents": None,
    "pyq": None,
    "syllabus": None,
    "fees": None,
    "pdfs": None,
    "uni_notices": None,
    "last_refresh": 0,
}
CACHE_TTL = 300  # Refresh cache every 5 minutes

# Base system prompt (compact — no bloated data)
HPTU_SYSTEM_PROMPT = """You are the official AI Assistant for Himachal Pradesh Technical University (HPTU), Hamirpur.
You were created by **Kunal Chauhan**, a B.Tech CSE student at HPTU, as a capstone project.

KEY FACTS:
- Full Name: Himachal Pradesh Technical University (HPTU)
- Location: Daruhi, Hamirpur, Himachal Pradesh - 177001
- Established: 2010 | Type: State Technical University
- Website: www.himtu.ac.in
- Vice Chancellor: Dr. Abhishek Jain (IAS)
- Programs: B.Tech, M.Tech, BBA, MBA, BCA, MCA, B.Pharmacy, M.Pharmacy, Diploma, Ph.D
- Branches: CSE, ECE, EE, ME, CE, IT, and more
- Admissions: B.Tech via HPCET/JEE Main | MBA via HPCET/MAT/CMAT | M.Tech via GATE/HPCET

IMPORTANT LINKS:
- Official: https://www.himtu.ac.in
- Exam Portal: https://hptuexam.com/
- Results: https://himachal-pradesh.indiaresults.com/himtu/default.aspx
- Fee Payment: https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?corpID=2471557
- Notice Board: https://www.himtu.ac.in/notice-board
- Date Sheets: https://www.himtu.ac.in/en/examination/examination-schedule
- Forms: https://www.himtu.ac.in/en/student-zone/forms
- Admissions: https://www.himtu.ac.in/en/admissions
- PYQ Papers: https://www.hptuonline.com/

CONTACTS: Registrar: 01972-226902 | Exam: 01972-226912 | Email: registrarhimtu@gmail.com

RESPONSE RULES:
1. Reply naturally like a helpful AI — be concise, friendly, and to the point.
2. When asked for documents/papers, provide DIRECT LINKS from the data below.
3. For PYQ/question papers:
   - If the user specifies course + branch + semester + subject, find and provide direct download links.
   - If the user only says "PYQ" or "question papers" without details, ask them to specify:
     a) Course (B.Tech, BBA, BCA, MBA, MCA, B.Pharmacy, M.Pharmacy, etc.)
     b) Branch (for B.Tech: CSE/IT, Civil, ME, Electrical, etc.)
     c) Semester (1-8)
     d) Subject (optional)
   - Always provide the direct hptuonline.com paper links when available.
   - Format each paper with subject name, exam period, and clickable link.
4. Keep answers short unless the user asks for detailed info.
5. Use bullet points and emojis for readability.
6. If you don't have specific data, give the relevant portal link.
7. For general knowledge questions (not HPTU-specific), answer directly from your knowledge.
8. When asked "who made you" or "who created you", credit **Kunal Chauhan** (B.Tech CSE, HPTU)."""


def _refresh_cache():
    """Refresh the in-memory cache from MongoDB (runs max once per CACHE_TTL)."""
    now = time.time()
    if now - _context_cache["last_refresh"] < CACHE_TTL:
        return  # Cache is still fresh

    try:
        from backend.services.notice_service import (
            load_hptu_notices, load_notices, load_syllabus, load_fees,
            load_scraped_pdfs, load_documents, load_pyq
        )
        _context_cache["notices"] = load_hptu_notices() or []
        _context_cache["documents"] = load_documents() or []
        _context_cache["pyq"] = load_pyq() or []
        _context_cache["syllabus"] = load_syllabus() or []
        _context_cache["fees"] = load_fees() or []
        _context_cache["pdfs"] = load_scraped_pdfs() or []
        _context_cache["uni_notices"] = load_notices() or {}
        _context_cache["last_refresh"] = now
    except Exception as e:
        print(f"Cache refresh error: {e}")


def _detect_query_topics(user_msg):
    """Detect what topics the user is asking about to load only relevant data."""
    msg = user_msg.lower()
    topics = set()

    # PYQ / Question papers
    if any(w in msg for w in ["pyq", "question paper", "previous year", "old paper",
                               "sample paper", "model paper", "past paper", "exam paper"]):
        topics.add("pyq")

    # Notices
    if any(w in msg for w in ["notice", "notification", "circular", "announcement", "latest update"]):
        topics.add("notices")

    # Results
    if any(w in msg for w in ["result", "marks", "grade", "marksheet", "cgpa", "sgpa"]):
        topics.add("notices")
        topics.add("documents")

    # Date sheet / Exam
    if any(w in msg for w in ["date sheet", "datesheet", "exam schedule", "examination"]):
        topics.add("documents")
        topics.add("notices")

    # Syllabus
    if any(w in msg for w in ["syllabus", "curriculum", "course", "subject"]):
        topics.add("syllabus")

    # Fees
    if any(w in msg for w in ["fee", "payment", "scholarship", "refund"]):
        topics.add("fees")
        topics.add("notices")

    # Admission
    if any(w in msg for w in ["admission", "admit", "hpcet", "entrance", "counseling",
                               "counselling", "jee", "gate"]):
        topics.add("documents")
        topics.add("notices")

    # Documents / Forms / Downloads
    if any(w in msg for w in ["download", "form", "pdf", "document", "admit card",
                               "calendar", "holiday"]):
        topics.add("documents")

    # If no specific topic detected, it's a general question — no heavy data needed
    return topics


def _search_items(items, query, fields=("title",), max_results=20):
    """Fast keyword search across a list of dicts."""
    query_words = query.lower().split()
    results = []
    for item in items:
        text = " ".join(str(item.get(f, "")) for f in fields).lower()
        score = sum(1 for w in query_words if w in text)
        if score > 0:
            results.append((score, item))
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:max_results]]


def _build_smart_context(user_message):
    """Build minimal, relevant context based on what the user is actually asking."""
    _refresh_cache()

    topics = _detect_query_topics(user_message)
    context_parts = []

    # If no specific topic — general question, skip heavy data
    if not topics:
        return ""

    # ── PYQ: Only include matching papers ──
    if "pyq" in topics:
        pyq_papers = _search_items(
            _context_cache.get("pyq", []),
            user_message,
            fields=("title", "course", "branch", "subject"),
            max_results=30
        )
        if pyq_papers:
            pyq_text = "\n📝 MATCHING PYQ PAPERS (from hptuonline.com):\n"
            for p in pyq_papers:
                subject = p.get('subject', p.get('title', ''))
                pyq_text += f"  • {subject}"
                if p.get('course'):
                    pyq_text += f" [{p['course']}"
                    if p.get('branch'):
                        pyq_text += f" - {p['branch']}"
                    pyq_text += "]"
                if p.get('semester'):
                    pyq_text += f" | Sem {p['semester']}"
                if p.get('exam_period'):
                    pyq_text += f" | {p['exam_period']}"
                if p.get('link'):
                    pyq_text += f"\n    🔗 {p['link']}"
                pyq_text += "\n"
            context_parts.append(pyq_text)
        else:
            # List available courses/branches to help user navigate
            context_parts.append(
                "\n📝 PYQ: No exact match found for the query. "
                "Available courses: B.Tech (CSE/IT, Civil, ME, Electrical, Auto, Textile), "
                "BBA, BCA, BHMCT, B.Pharmacy, MBA, MCA, M.Pharmacy, M.Sc, M.Tech, Ph.D, Yoga, HPTSB Diploma, HPTSB ITI.\n"
                "Ask the user to specify: 1) Course 2) Branch (if B.Tech) 3) Semester 4) Subject (optional).\n"
                "Direct link: https://www.hptuonline.com/\n"
            )

    # ── Notices: Only top 10 recent ──
    if "notices" in topics:
        notices = _context_cache.get("notices", [])[:10]
        if notices:
            notice_text = "\n📋 LATEST NOTICES:\n"
            for n in notices:
                notice_text += f"  • {n.get('title', '')} ({n.get('date', '')})"
                if n.get('link'):
                    notice_text += f"\n    📄 {n['link']}"
                notice_text += "\n"
            context_parts.append(notice_text)

    # ── Documents: Only matching ones ──
    if "documents" in topics:
        docs = _search_items(
            _context_cache.get("documents", []),
            user_message,
            fields=("title", "category", "program"),
            max_results=15
        )
        if docs:
            doc_text = "\n📂 MATCHING DOCUMENTS:\n"
            for d in docs:
                doc_text += f"  • {d.get('title', '')} [{d.get('category', '')}]"
                if d.get('link'):
                    doc_text += f"\n    🔗 {d['link']}"
                doc_text += "\n"
            context_parts.append(doc_text)

    # ── Syllabus ──
    if "syllabus" in topics:
        syllabus = _search_items(
            _context_cache.get("syllabus", []),
            user_message,
            fields=("title", "program"),
            max_results=10
        )
        if syllabus:
            syl_text = "\n📚 SYLLABUS:\n"
            for s in syllabus:
                syl_text += f"  • {s.get('title', '')}"
                if s.get('link'):
                    syl_text += f"\n    📄 {s['link']}"
                syl_text += "\n"
            context_parts.append(syl_text)

    # ── Fees ──
    if "fees" in topics:
        fees = _context_cache.get("fees", [])[:10]
        if fees:
            fees_text = "\n💰 FEES INFO:\n"
            for f in fees:
                if f.get('description'):
                    fees_text += f"  • {f['description']}\n"
                elif f.get('title'):
                    fees_text += f"  • {f['title']}"
                    if f.get('link'):
                        fees_text += f" — {f['link']}"
                    fees_text += "\n"
            context_parts.append(fees_text)

    return "\n".join(context_parts)


def get_chat_response(user_message, pdf_text=""):
    """
    Fast AI chat — only loads relevant context, uses lighter model for general queries.
    """
    from backend import co

    normalized = (user_message or "").lower().strip()
    has_roll = re.search(r"\b\d{5,15}\b", user_message or "") is not None
    is_result_intent = (
        "result" in normalized
        or "roll" in normalized
        or "marksheet" in normalized
        or (has_roll and any(k in normalized for k in ["sem", "semester", "btech", "hptu"]))
        or normalized.isdigit()
    )

    # Result lookups are handled with deterministic scraping, not LLM generation.
    if is_result_intent:
        try:
            from backend.services.result_service import handle_btech_5th_result_query
            reply = handle_btech_5th_result_query(user_message)

            log_entry = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "user": user_message[:100],
                "bot": reply[:150],
            }
            chat_logs.append(log_entry)
            if len(chat_logs) > 50:
                chat_logs.pop(0)

            try:
                from backend.services.notice_service import save_chat_log
                save_chat_log(user_message, reply)
            except Exception:
                pass

            return reply
        except Exception as e:
            print(f"Result intent handler error: {e}")

    if not co:
        return "AI service is not configured. Please set the COHERE_API_KEY."

    try:
        start = time.time()

        # Build ONLY relevant context (not everything)
        smart_context = _build_smart_context(user_message)

        system_prompt = HPTU_SYSTEM_PROMPT

        if smart_context:
            system_prompt += f"\n\nRELEVANT DATA:\n{smart_context}"

        if pdf_text:
            system_prompt += f"\n\nUSER UPLOADED PDF CONTENT:\n{pdf_text[:8000]}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Use faster model for general questions, full model only when data-heavy
        topics = _detect_query_topics(user_message)
        model = "command-r7b-12-2024" if not topics else "command-a-03-2025"

        response = co.chat(
            model=model,
            messages=messages,
        )

        reply = response.message.content[0].text
        elapsed = round(time.time() - start, 1)
        print(f"⚡ Chat response in {elapsed}s (model={model}, topics={topics or 'general'})")

    except Exception as e:
        print("Chat Error:", e)
        reply = "I'm sorry, I'm having trouble connecting right now. Please try again in a moment."

    # Log conversation
    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_message[:100],
        "bot": reply[:150],
    }
    chat_logs.append(log_entry)
    if len(chat_logs) > 50:
        chat_logs.pop(0)

    try:
        from backend.services.notice_service import save_chat_log
        save_chat_log(user_message, reply)
    except Exception:
        pass

    return reply


def clear_chat_logs():
    """Clear all stored chat logs."""
    chat_logs.clear()
    try:
        from backend.services.notice_service import clear_chat_logs_db
        clear_chat_logs_db()
    except Exception:
        pass
