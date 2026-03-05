"""
Chat Service — Cohere AI chatbot logic and conversation logging
"""
from datetime import datetime

# In-memory chat logs (visible in admin dashboard)
chat_logs = []

# HPTU Knowledge base system prompt
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


def get_chat_response(user_message, pdf_text=""):
    """
    Send a message to the Cohere AI and return the response.
    Includes PDF context if a document has been uploaded.
    """
    from backend import co  # Lazy import to avoid circular dependency

    if not co:
        return "AI service is not configured. Please set the COHERE_API_KEY."

    try:
        messages = []

        if pdf_text:
            system_prompt = HPTU_SYSTEM_PROMPT + f"""

A PDF document has been uploaded. Use its content to answer questions when relevant.

PDF Content:
{pdf_text[:15000]}
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

    # Log the conversation for admin dashboard
    chat_logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_message[:100],
        "bot": reply[:150],
    })
    # Keep only last 50 logs in memory
    if len(chat_logs) > 50:
        chat_logs.pop(0)

    return reply


def clear_chat_logs():
    """Clear all stored chat logs."""
    chat_logs.clear()
