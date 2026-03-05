"""
Chat Service — Cohere AI chatbot with real-time HPTU data knowledge
Pulls latest notices, PDFs, syllabus, fees, documents from MongoDB to answer queries.
Always provides direct PDF/document links when users ask for any document.
"""
from datetime import datetime

# In-memory chat logs (also persisted to MongoDB)
chat_logs = []

# Base system prompt
HPTU_SYSTEM_PROMPT = """You are the official AI Assistant for Himachal Pradesh Technical University (HPTU), Hamirpur.
You help students, faculty, and visitors with university-related queries.

ABOUT YOUR CREATOR:
- You were created and developed by **Kunal Chauhan**, a B.Tech Computer Science & Engineering (CSE) student at HPTU.
- When anyone asks "who made you", "who created you", "who built you", "who is your developer",
  "who designed you", or any similar question about your origin/creator, you MUST answer:
  "I was created by **Kunal Chauhan**, a B.Tech CSE student at Himachal Pradesh Technical University (HPTU), Hamirpur.
  He developed me as a capstone project to help students, faculty, and visitors get real-time information about HPTU."
- Always credit Kunal Chauhan proudly and mention he is a B.Tech CSE student at HPTU.

KEY FACTS ABOUT HPTU:
- Full Name: Himachal Pradesh Technical University (HPTU)
- Location: Daruhi, Hamirpur, Himachal Pradesh, India - 177001
- Established: 2010 under HP Technical University Act
- Type: State Technical University
- Website: www.himtu.ac.in
- Chancellor: Governor of Himachal Pradesh
- Vice Chancellor: Dr. Abhishek Jain (IAS)
- Affiliation: Affiliates engineering, pharmacy, management, and other technical colleges across HP

ACADEMICS:
- Offers B.Tech, M.Tech, BBA, MBA, BCA, MCA, B.Pharmacy, M.Pharmacy, B.Arch, Diploma, Ph.D programs
- Branches: CSE, ECE, EE, ME, CE, IT, and more
- Semester system with university-conducted exams

ADMISSIONS:
- B.Tech: HPCET / JEE Main
- MBA: HPCET / MAT / CMAT
- M.Tech: GATE / HPCET
- Lateral entry for diploma holders

IMPORTANT PORTALS & LINKS:
- Official Website: https://www.himtu.ac.in
- Examination Portal (Admit Cards & Forms): https://hptuexam.com/
- Results Portal: https://himachal-pradesh.indiaresults.com/himtu/default.aspx
- Online Fee Payment (SBI Collect): https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?corpID=2471557
- Notice Board: https://www.himtu.ac.in/notice-board
- Examination Schedule / Date Sheets: https://www.himtu.ac.in/en/examination/examination-schedule
- Student Forms (Download): https://www.himtu.ac.in/en/student-zone/forms
- DigiLocker (Certificates): https://nad.digilocker.gov.in/
- Admissions Page: https://www.himtu.ac.in/en/admissions
- Student Zone: https://www.himtu.ac.in/en/student-zone

CONTACTS:
- Address: Daruhi, Hamirpur, HP - 177001
- Registrar Office: 01972-226902
- Examination/Degree queries: 01972-226912, 01972-226908, 01972-226910, 01972-226999
- Email: registrarhimtu@gmail.com

═══════════════════════════════════════════════════════
CRITICAL RESPONSE RULES — YOU MUST FOLLOW THESE:
═══════════════════════════════════════════════════════

1. **ALWAYS PROVIDE DIRECT LINKS**: When a user asks for ANY document (academic calendar, date sheet,
   syllabus, fee notice, admit card, result, form, circular, notification, PDF, etc.),
   you MUST provide the direct download link or URL from the REAL-TIME DATA below.
   NEVER say "check the website" without giving the actual link.

2. **LINK FORMAT**: Always provide clickable links. Format like:
   📄 Document Name: <link>
   If multiple documents match, list ALL of them with their links.

3. **SEARCH THOROUGHLY**: Search through ALL the data sections below — NOTIFICATIONS, DOCUMENTS,
   SYLLABUS, FEES, and SCRAPED PDFs — to find relevant links for the user's query.
   A user asking for "academic calendar" might find it in notices OR documents.

4. **PDF CONTENT KNOWLEDGE**: You have access to extracted text from PDFs. Use this knowledge
   to answer specific questions about what's INSIDE documents (dates, schedules, rules, etc.)

5. **FALLBACK LINKS**: If you cannot find the exact document, provide the most relevant portal link:
   - For date sheets/exams → https://www.himtu.ac.in/en/examination/examination-schedule
   - For results → https://himachal-pradesh.indiaresults.com/himtu/default.aspx
   - For admit cards → https://hptuexam.com/
   - For fee payment → https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?corpID=2471557
   - For forms → https://www.himtu.ac.in/en/student-zone/forms
   - For all notices → https://www.himtu.ac.in/notice-board
   - For admissions → https://www.himtu.ac.in/en/admissions

6. **BE SPECIFIC**: Don't give vague answers. If user asks "where can I download B.Tech date sheet?",
   find the exact PDF link from the data and share it.

7. **MULTIPLE MATCHES**: If multiple documents match the query, list them ALL with dates so the
   user can pick the right one.

GENERAL RESPONSE GUIDELINES:
- Be helpful, accurate, and professional
- Format responses clearly with bullet points when listing information
- Keep responses concise but informative
- Always be polite and supportive to students
- If you truly don't have a specific document, say so honestly and give the portal link where they can find it"""


def _build_realtime_context():
    """Build real-time context from MongoDB data for the AI chatbot."""
    from backend.services.notice_service import (
        load_hptu_notices, load_notices, load_syllabus, load_fees,
        load_scraped_pdfs, load_documents
    )

    context_parts = []

    # ── Current HPTU notices with direct PDF links ──
    try:
        hptu_notices = load_hptu_notices()
        if hptu_notices:
            notice_text = "\n\n📋 CURRENT HPTU NOTIFICATIONS (with direct PDF links):\n"
            for i, n in enumerate(hptu_notices[:30], 1):
                notice_text += f"\n{i}. 📌 {n.get('title', 'N/A')}"
                if n.get('date'):
                    notice_text += f"\n   Date: {n['date']}"
                if n.get('last_date'):
                    notice_text += f" | Deadline: {n['last_date']}"
                if n.get('category'):
                    notice_text += f"\n   Category: {n['category']}"
                if n.get('link'):
                    notice_text += f"\n   📄 DIRECT LINK: {n['link']}"
                notice_text += "\n"

                # Include PDF text if available (for answering content questions)
                pdf_text = n.get('pdf_text', '')
                if pdf_text:
                    notice_text += f"   [PDF Content]: {pdf_text[:400]}\n"

            context_parts.append(notice_text)
    except Exception as e:
        print(f"Context build error (notices): {e}")

    # ── Documents & Resources (date sheets, forms, exam schedules, etc.) ──
    try:
        documents = load_documents()
        if documents:
            doc_text = "\n\n📂 HPTU DOCUMENTS & RESOURCES (searchable by category):\n"

            # Group by category for better organization
            by_cat = {}
            for d in documents:
                cat = d.get('category', 'general')
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(d)

            category_labels = {
                "date_sheet": "📅 DATE SHEETS",
                "academic_calendar": "📆 ACADEMIC CALENDAR",
                "admit_card": "🎫 ADMIT CARDS",
                "results": "📊 RESULTS",
                "syllabus": "📚 SYLLABUS",
                "fees": "💰 FEES",
                "fee_payment": "💳 FEE PAYMENT",
                "forms": "📝 FORMS",
                "admission": "🎓 ADMISSION",
                "circulars": "📜 CIRCULARS",
                "examination_portal": "🖥️ EXAMINATION PORTAL",
                "certificates": "📜 CERTIFICATES",
                "holiday_calendar": "📅 HOLIDAYS",
                "special_chance": "🔄 SPECIAL CHANCE",
                "revaluation": "🔍 REVALUATION",
                "tender": "📋 TENDERS",
                "general": "ℹ️ GENERAL",
            }

            for cat, items in by_cat.items():
                label = category_labels.get(cat, cat.upper())
                doc_text += f"\n  {label}:\n"
                for d in items[:10]:  # max 10 per category
                    doc_text += f"    • {d.get('title', 'N/A')}"
                    if d.get('program') and d['program'] != 'General':
                        doc_text += f" [{d['program']}]"
                    if d.get('link'):
                        doc_text += f"\n      🔗 LINK: {d['link']}"
                    doc_text += "\n"

            context_parts.append(doc_text)
    except Exception as e:
        print(f"Context build error (documents): {e}")

    # ── University announcements ──
    try:
        uni_notices = load_notices()
        if uni_notices:
            uni_text = "\n📢 UNIVERSITY ANNOUNCEMENTS:\n"
            for nid, n in uni_notices.items():
                uni_text += f"- {n.get('title', '')}: {n.get('description', '')} ({n.get('date', '')})\n"
            context_parts.append(uni_text)
    except Exception:
        pass

    # ── Syllabus data with download links ──
    try:
        syllabus = load_syllabus()
        if syllabus:
            syl_text = "\n📚 AVAILABLE SYLLABUS/CURRICULUM:\n"
            for s in syllabus[:20]:
                syl_text += f"- {s.get('title', 'N/A')}"
                if s.get('program'):
                    syl_text += f" ({s['program']})"
                if s.get('link'):
                    syl_text += f"\n  📄 Download: {s['link']}"
                syl_text += "\n"
            context_parts.append(syl_text)
    except Exception:
        pass

    # ── Fees data with links ──
    try:
        fees = load_fees()
        if fees:
            fees_text = "\n💰 FEE STRUCTURE INFORMATION:\n"
            for f in fees[:15]:
                if f.get('description'):
                    fees_text += f"- {f['description']}\n"
                elif f.get('title'):
                    fees_text += f"- {f['title']}"
                    if f.get('link'):
                        fees_text += f"\n  📄 Details: {f['link']}"
                    fees_text += "\n"
            context_parts.append(fees_text)
    except Exception:
        pass

    # ── Scraped PDF content (for answering questions about content inside PDFs) ──
    try:
        pdfs = load_scraped_pdfs()
        if pdfs:
            pdf_context = "\n📄 EXTRACTED CONTENT FROM HPTU PDF DOCUMENTS:\n"
            total_chars = 0
            for pdf in pdfs[:10]:
                text = pdf.get("text", "")
                if text and total_chars < 6000:
                    pdf_context += f"\n--- {pdf.get('title', 'Document')} ---\n"
                    if pdf.get('url'):
                        pdf_context += f"PDF Link: {pdf['url']}\n"
                    remaining = 6000 - total_chars
                    pdf_context += text[:remaining] + "\n"
                    total_chars += min(len(text), remaining)
            context_parts.append(pdf_context)
    except Exception:
        pass

    return "\n".join(context_parts)


def get_chat_response(user_message, pdf_text=""):
    """
    Send a message to the Cohere AI with real-time HPTU data context.
    Includes user-uploaded PDF context if available.
    """
    from backend import co

    if not co:
        return "AI service is not configured. Please set the COHERE_API_KEY."

    try:
        # Build system prompt with real-time data
        realtime_context = _build_realtime_context()

        system_prompt = HPTU_SYSTEM_PROMPT

        if realtime_context:
            system_prompt += f"\n\n{'='*50}\nREAL-TIME HPTU DATA (auto-updated from official website):\n{'='*50}\n"
            system_prompt += realtime_context

        if pdf_text:
            system_prompt += f"\n\n{'='*50}\nUSER UPLOADED PDF CONTENT:\n{'='*50}\n"
            system_prompt += pdf_text[:15000]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = co.chat(
            model="command-a-03-2025",
            messages=messages,
        )

        reply = response.message.content[0].text

    except Exception as e:
        print("Chat Error:", e)
        reply = "I'm sorry, I'm having trouble connecting to the AI service right now. Please try again in a moment."

    # Log the conversation (in-memory + MongoDB)
    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_message[:100],
        "bot": reply[:150],
    }
    chat_logs.append(log_entry)
    if len(chat_logs) > 50:
        chat_logs.pop(0)

    # Persist to MongoDB
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
