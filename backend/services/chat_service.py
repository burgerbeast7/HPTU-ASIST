"""
Chat Service — Fast AI chatbot with smart context loading
Only loads relevant data based on user query. Caches context. Uses faster model.
"""
import time
import re
from datetime import datetime

# Common filler words removed during token scoring.
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "please", "show", "tell",
    "the", "to", "what", "when", "where", "which", "who", "with", "my", "your",
    "do", "does", "can", "could", "would", "should", "about", "latest", "new",
}

HPTU_DOMAIN_KEYWORDS = {
    "hptu", "himtu", "hamirpur", "hpcet", "hptuonline", "indiaresults",
    "btech", "mtech", "bba", "bca", "mba", "mca", "bpharmacy", "mpharmacy",
    "result", "results", "datesheet", "date sheet", "syllabus", "notice", "admission",
    "exam", "semester", "roll", "fee", "fees", "registration", "forms",
}

NAME_EXCLUDE_TOKENS = {
    "hptu", "himtu", "exam", "schedule", "syllabus", "notice", "admission",
    "result", "roll", "semester", "sem", "fee", "fees", "date", "when",
    "what", "who", "where", "why", "how", "link", "portal", "help",
}

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

ACADEMIC CALENDAR 2025-26 (Even Semester):
- End of Teaching work: May 22, 2026
- End Semester Practical Exams: May 25, 2026 to May 28, 2026
- End Semester Theory Exams: May 29, 2026 to June 15, 2026
- Summer Vacations: June 18, 2026 to July 16, 2026

CONTACTS & HELPDESK (for student issues):
- Registrar Office: 01972-226902 | registrarhimtu@gmail.com (general queries, migration, name correction, bonafide)
- Controller of Examinations: 01972-226912 | exam.himtu@gmail.com (result issues, re-evaluation, date sheets, mark sheets, exam forms)
- Admission Cell: 01972-226902 | admissionhimtu@gmail.com (admission queries, seat allotment, counselling)
- Fee Section / Finance: 01972-226902 (fee payment issues, refund, scholarship queries)
- Dean (Academic): For academic calendar, syllabus, course structure issues
- Dean (Student Welfare): For hostel, ragging, campus issues, student grievances
- Anti-Ragging Helpline: 1800-180-5522 (UGC national helpline)
- Official Grievance Portal: https://www.himtu.ac.in/en/student-zone/forms
- Fee Payment Portal: https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?corpID=2471557

COMMON STUDENT ISSUES & GUIDANCE:
1. Result not showing / wrong result → Contact Exam Branch: 01972-226912 or email exam.himtu@gmail.com with roll number and details.
2. Re-evaluation / Re-checking → Fill the re-evaluation form from https://www.himtu.ac.in/en/student-zone/forms, pay the fee, and submit to the Exam Branch within the deadline.
3. Name / DOB correction in marksheet → Submit an affidavit + correction form to the Registrar Office with supporting documents.
4. Migration certificate → Apply through the Registrar Office after clearing all dues. Submit No-Dues certificate.
5. Fee payment issue / receipt not generated → Contact Fee Section at 01972-226902 with transaction ID and screenshot.
6. Scholarship / fee refund → Contact the Finance Officer or visit https://www.himtu.ac.in for latest scholarship notices.
7. Exam form not submitted / late fee → Contact Exam Branch immediately at 01972-226912.
8. Hostel / campus issues → Report to Dean (Student Welfare) through your college administration.
9. Ragging complaint → Call Anti-Ragging Helpline 1800-180-5522 or email antiragging@himtu.ac.in.
10. Duplicate marksheet / degree → Apply through Registrar Office with an FIR copy and affidavit.
11. Backlog / reappear exam → Check date sheets at https://www.himtu.ac.in/en/examination/examination-schedule and fill the exam form before the deadline.
12. Internal assessment / attendance shortage → Contact your college HOD/Principal first, then Dean (Academic) if unresolved.

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
8. When asked "who made you" or "who created you", credit **Kunal Chauhan** (B.Tech CSE, HPTU).
9. Do NOT invent notice titles, dates, links, results, or PDF details. Use only provided data for HPTU-specific facts.
10. If required details are missing (for example course/branch/semester), ask a short clarifying question first.
11. If no exact match exists in the provided data, explicitly say so and share the closest official link.
12. When a student reports an ISSUE or PROBLEM (result issue, fee problem, hostel, ragging, exam form, name correction, migration, etc.):
    - Be empathetic and professional. Acknowledge their concern first.
    - Identify the issue category and provide the EXACT steps to resolve it from the COMMON STUDENT ISSUES section above.
    - Always include the correct contact number, email, and portal link for that issue.
    - If the issue is urgent (ragging, safety), prioritize the emergency helpline immediately.
13. When a student says something like "I need help", "I have a problem", or describes any difficulty, treat it as a helpdesk query and ask what specific issue they are facing, then guide accordingly.
14. Always end issue-related responses with a reassuring note like "Feel free to ask if you need more help!" to encourage students to reach out.

CONSULTANT & GUIDE ROLE:
You also act as a friendly university consultant and academic guide. When students ask for advice, guidance, or career-related questions, respond thoughtfully:

CAREER & BRANCH GUIDANCE:
- B.Tech CSE/IT → Software development, AI/ML, data science, cybersecurity, cloud computing. Top recruiters: TCS, Infosys, Wipro, HCL, Cognizant. Avg package: 4-8 LPA. Prep: DSA, coding platforms (LeetCode, CodeChef), projects, internships.
- B.Tech ECE → VLSI, embedded systems, IoT, telecom, chip design. Can also enter IT sector with coding skills.
- B.Tech ME → Core manufacturing, automobile, thermal, design (CATIA/SolidWorks). GATE for PSUs is a strong path.
- B.Tech CE → Construction, infrastructure, government jobs (SSC JE, State PWD). GATE for IITs/PSUs.
- B.Tech EE → Power sector, electrical design, PSU jobs (BHEL, NTPC, PGCIL via GATE).
- BBA/MBA → Marketing, finance, HR, operations. Corporate placements, startup ecosystem, or prepare for CAT/MAT for top B-schools.
- BCA/MCA → Software roles similar to B.Tech CSE. Focus on full-stack development, React, Node.js, Python.
- B.Pharmacy/M.Pharmacy → Pharma companies, drug inspector (GPAT), hospital pharmacist, research. GPAT for M.Pharmacy admission.

HIGHER STUDIES GUIDANCE:
- GATE → For M.Tech at IITs/NITs/HPTU or PSU jobs. Start prep in 3rd year. Key: previous year papers + coaching (online: Unacademy/NPTEL).
- CAT/MAT/CMAT → For MBA at IIMs/top colleges. Can attempt in final year.
- GRE/IELTS/TOEFL → For MS/MBA abroad. Start in 3rd year, build strong profile with projects and research papers.
- UPSC/State PSC → Engineering services or civil services after graduation.
- GPAT → For M.Pharmacy admissions. Pharmacy graduates should prepare alongside final year.

PLACEMENT PREPARATION TIPS:
- Start coding practice from 2nd year (LeetCode, HackerRank, GeeksforGeeks).
- Build 2-3 strong projects and host on GitHub.
- Learn at least one framework well (React, Django, Flutter, Spring Boot).
- Practice aptitude (RS Aggarwal) and verbal (Word Power Made Easy).
- Prepare for HR interviews: tell me about yourself, strengths/weaknesses, why this company.
- Get internships through Internshala, LinkedIn, college placement cell.
- Certifications: AWS, Google Cloud, NPTEL courses add value.

SEMESTER TIPS:
- 1st-2nd Sem: Focus on fundamentals, programming basics, and building good CGPA.
- 3rd-4th Sem: Start competitive coding, pick up a tech stack, do mini projects.
- 5th-6th Sem: Internships, major projects, start GATE/placement prep.
- 7th-8th Sem: Placements, final project, focus on interviews and communication skills.

GENERAL GUIDANCE RULES:
- When asked "what should I do after B.Tech?" or career advice, provide specific actionable paths based on their branch.
- When asked about placements, share realistic expectations and preparation tips.
- When asked "which branch is best?", be neutral — explain strengths of each and ask about their interests.
- When a student seems confused or stressed, be supportive and encouraging. Motivate them.
- For questions about competitive exams (GATE, CAT, UPSC), share preparation roadmaps and timelines."""


def _normalize_text(text):
    """Normalize free text for matching/scoring."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokenize(text):
    """Tokenize text while dropping filler words."""
    normalized = _normalize_text(text)
    return {t for t in normalized.split() if t and t not in STOP_WORDS and len(t) > 1}


def _extract_semester_number(text):
    """Extract requested semester from query if present."""
    normalized = _normalize_text(text)
    sem_match = re.search(r"\b([1-8])(?:st|nd|rd|th)?\s*(?:sem|semester)\b", normalized)
    if sem_match:
        return int(sem_match.group(1))
    return 0


def _is_hptu_domain_query(user_msg):
    """Detect if the question is likely HPTU-domain and should prefer stronger grounding."""
    msg = _normalize_text(user_msg)
    if any(keyword in msg for keyword in HPTU_DOMAIN_KEYWORDS):
        return True

    # Roll-number style queries are usually result/domain-specific.
    if re.search(r"\b\d{5,15}\b", msg):
        return True

    return False


def _looks_like_candidate_name_query(user_msg):
    """Heuristic: detect plain full-name inputs for result-by-name lookup."""
    raw = (user_msg or "").strip()
    # Tolerate common trailing punctuation in chat input.
    raw = re.sub(r"[\?\!\.,;:]+$", "", raw)
    msg = _normalize_text(raw)
    if not msg:
        return False

    # Avoid triggering on complex sentence-like queries.
    if any(ch in raw for ch in "@#$/\\"):
        return False

    tokens = msg.split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False

    for token in tokens:
        if not token.isalpha():
            return False
        if token in NAME_EXCLUDE_TOKENS:
            return False
        if len(token) < 2:
            return False

    return True


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


def _search_items(items, query, fields=("title",), max_results=20, min_score=1.0):
    """Weighted search across list items for better precision on mixed user queries."""
    query_norm = _normalize_text(query)
    query_tokens = _tokenize(query)
    requested_sem = _extract_semester_number(query)
    results = []

    for item in items:
        raw_text = " ".join(str(item.get(f, "")) for f in fields)
        item_norm = _normalize_text(raw_text)
        if not item_norm:
            continue

        item_tokens = _tokenize(raw_text)
        score = 0.0

        # Strong signal: full phrase hit.
        if query_norm and query_norm in item_norm:
            score += 6.0

        # Token overlap for partial intent matches.
        overlap = len(query_tokens & item_tokens)
        score += overlap * 1.5

        # Prefix overlap catches partial words like "elect" -> "electrical".
        for token in query_tokens:
            if len(token) >= 4 and any(it.startswith(token) for it in item_tokens):
                score += 0.25

        # Semester consistency is important for PYQ/syllabus lookups.
        item_sem = int(item.get("semester", 0) or 0)
        if requested_sem and item_sem:
            if requested_sem == item_sem:
                score += 2.0
            else:
                score -= 1.0

        if score >= min_score:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:max_results]]


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
            max_results=20,
            min_score=2.0,
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
        notices = _search_items(
            _context_cache.get("notices", []),
            user_message,
            fields=("title", "date", "last_date", "category"),
            max_results=10,
            min_score=1.0,
        )
        if not notices:
            notices = _context_cache.get("notices", [])[:5]
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
            max_results=12,
            min_score=1.6,
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
            max_results=10,
            min_score=1.4,
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
        fees = _search_items(
            _context_cache.get("fees", []),
            user_message,
            fields=("title", "description", "program", "category"),
            max_results=10,
            min_score=1.0,
        )
        if not fees:
            fees = _context_cache.get("fees", [])[:5]
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

    # Live timeline/date questions (e.g., HPCET date) are handled through
    # deterministic web lookup to improve factual accuracy and keep replies concise.
    try:
        from backend.services.web_lookup_service import lookup_exact_date_details

        date_lookup = lookup_exact_date_details(user_message)
        if date_lookup.get("ok"):
            reply = date_lookup.get("answer", "")

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

        if date_lookup.get("reason") in {"no_exact_date_found", "no_search_results"}:
            fallback_link = date_lookup.get("fallback_link", "https://www.himtu.ac.in/en/admissions")
            return (
                "I could not confirm an exact official date right now. "
                f"Please check this official source: {fallback_link}"
            )
    except Exception as e:
        print(f"Date lookup handler error: {e}")

    normalized = (user_message or "").lower().strip()
    has_roll = re.search(r"\b\d{5,15}\b", user_message or "") is not None
    has_plain_name = _looks_like_candidate_name_query(user_message or "")
    is_result_intent = (
        "result" in normalized
        or "roll" in normalized
        or "marksheet" in normalized
        or "name" in normalized
        or (has_roll and any(k in normalized for k in ["sem", "semester", "btech", "hptu"]))
        or normalized.isdigit()
        or has_plain_name
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
            # Keep result flow deterministic for the chat screen.
            return (
                "I could not fetch the result right now due to a temporary issue.\n"
                "Please try again in a moment.\n"
                "Result portal: https://himturesult.indiaresults.com/hp/himtu/hp-himtu/query.aspx?id=1800266751"
            )

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

        # Prefer stronger model for HPTU-domain questions and context-heavy requests.
        topics = _detect_query_topics(user_message)
        is_hptu_domain = _is_hptu_domain_query(user_message)
        model = "command-a-03-2025" if topics or is_hptu_domain else "command-r7b-12-2024"

        response = co.chat(
            model=model,
            messages=messages,
            temperature=0.2,
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
