# 🎓 HPTU AI Assistant

An AI-powered smart helpdesk system for **Himachal Pradesh Technical University (HPTU)**, Hamirpur. Built as a Capstone Project, it provides real-time university information through an intelligent chatbot, auto-scraped notifications, syllabus, fee structures, and downloadable documents — all in one place.

🌐 **Live Demo:** [https://burgerbeast-projects.onrender.com](https://burgerbeast-projects.onrender.com)

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-green?logo=flask)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-darkgreen?logo=mongodb)
![Cohere AI](https://img.shields.io/badge/Cohere-AI%20Chatbot-purple?logo=data:image/svg+xml;base64,)
![License](https://img.shields.io/badge/License-MIT-yellow)
[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Render-brightgreen?logo=render)](https://burgerbeast-projects.onrender.com)

---

## 👨‍💻 Developer

| | |
|---|---|
| **Name** | **Kunal Chauhan** |
| **Program** | B.Tech — Computer Science & Engineering (CSE) |
| **University** | Himachal Pradesh Technical University (HPTU), Hamirpur |
| **Project Type** | Capstone Project |

---

## ✨ Features

### 🤖 AI Chatbot (Cohere-powered)
- Real-time conversational assistant trained on HPTU data
- Answers queries about admissions, exams, results, fees, syllabus, and more
- Provides **direct PDF/document download links** in responses
- Supports user-uploaded PDF scanning and Q&A
- Markdown-formatted responses with clickable links

### 🎓 Exam Results Lookup
- Search exam results by **roll number** or **student name**
- Multi-exam fallback system for legacy results (cascades through recent exams if not found in default)
- Real-time parsing of HPTU/IndiaResults portal data
- Displays student name, result status (PASS/FAIL), SGPA, CGPA, and subject-wise marks with grades
- Integrated directly into chat — just type "result [roll no]" or "[student name]"

### 📅 Live Web Search for Exam Dates
- Exact date lookups using Google Custom Search API (with DuckDuckGo fallback)
- Answers queries like "When was HPCET exam 2026?" with precise dates and sources
- Date pattern extraction (DDth MMMM YYYY, MMMM DD YYYY, DD/MM/YYYY formats)
- Includes source links and official HPTU website references

### 🎤 Voice Command Input
- Speak your queries using the built-in microphone button
- Uses the **Web Speech API** for real-time speech-to-text
- Supports English (India) locale
- Auto-sends the message after speech is recognized
- Visual feedback with animated pulse indicator while listening

### 📄 Previous Year Question Papers (PYQ)
- Scrapes **1000+ question papers** from [hptuonline.com](https://www.hptuonline.com)
- Covers all courses: B.Tech (8 branches), BBA, BCA, MBA, MCA, B.Pharmacy, M.Pharmacy, M.Sc, M.Tech, Ph.D, Yoga, HPTSB Diploma/ITI
- **Structured data extraction**: subject name, semester, exam period, paper code
- Interactive chatbot flow — asks for course → branch → semester → subject before providing download links
- Searchable via API with course/branch/semester filters

### 📋 Auto-Scraping System
- Scrapes the official [himtu.ac.in](https://www.himtu.ac.in) notice board with **multi-page support** (50+ notices)
- Proper 5-column table parsing: Title, Date, Expiry, Link, Attachments
- Extracts notices, date sheets, exam schedules, circulars, forms, and fee notifications
- Downloads and extracts text from PDF documents for AI knowledge
- Scrapes **8 HPTU pages** and collects **55+ documents** with direct links
- Background scheduling via APScheduler

### 📂 Document & Resource Hub
- Live notifications from HPTU notice board
- Filterable notices by category (Examination, Admission, Fees, Syllabus, Recruitment)
- Syllabus section with download links
- Fee structure section with amount details
- Category badges and AI-scanned indicators

### 🔐 Admin Dashboard
- Secure login with brute-force protection
- Manual scraper trigger and status monitoring
- View chat logs and scraper statistics
- Manage notices and university data

### 🔍 Intelligent Query Routing
- **Intent Detection System**: Automatically recognizes result queries (by roll number or student name) vs. general queries
- **Date Query Processing**: Extracts and validates dates using regex patterns (DDth MMMM YYYY, etc.)
- **Fallback Architecture**: Multi-exam result lookup cascades through recent exam sessions if result not found in default exam

### 🎨 UI/UX
- Themed to match the official HPTU website (navy blue + gold palette)
- Fully responsive design (mobile, tablet, desktop)
- Live stats bar showing real-time data counts
- Floating chatbot with typing indicators

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, Flask 3.1 (Blueprints) |
| **AI Engine** | Cohere API (command-a-03-2025 / command-r7b-12-2024) |
| **Database** | MongoDB (pymongo 4.7) |
| **Web Scraping** | BeautifulSoup4, Requests (himtu.ac.in + hptuonline.com) |
| **PDF Processing** | pypdf |
| **Task Scheduler** | APScheduler 3.10 |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla) |
| **Deployment** | Render (Gunicorn) |

---

## 📁 Project Structure

```
HPTU-AI-Assistant/
├── run.py                      # Application entry point
├── config.py                   # Configuration & environment settings
├── requirements.txt            # Python dependencies
├── Procfile                    # Render deployment config
├── render.yaml                 # Render service config
├── .env                        # Environment variables (API keys)
│
├── backend/                    # Backend application
│   ├── __init__.py             # Flask app factory, MongoDB init, scheduler
│   ├── db.py                   # MongoDB connection module
│   ├── routes/
│   │   ├── main_routes.py      # Home page & PDF upload routes
│   │   ├── api_routes.py       # REST API endpoints (notices, syllabus, fees)
│   │   └── admin_routes.py     # Admin dashboard & scraper controls
│   └── services/
│       ├── chat_service.py         # Cohere AI chatbot with real-time context
│       ├── result_service.py       # HPTU exam result lookup (by roll/name, multi-exam fallback)
│       ├── web_lookup_service.py   # Live web search for exam dates (Google + DuckDuckGo)
│       ├── scraper_service.py      # HPTU website scraper (notices, docs, PDFs)
│       ├── pyq_service.py          # PYQ scraper for hptuonline.com (structured data)
│       ├── notice_service.py       # MongoDB CRUD for notices, syllabus, fees, docs, PYQ
│       └── pdf_service.py          # PDF text extraction service
│
├── frontend/                   # Frontend application
│   ├── templates/
│   │   ├── index.html          # Main page (notices, syllabus, fees, chatbot)
│   │   └── admin/
│   │       └── dashboard.html  # Admin dashboard
│   └── static/
│       ├── css/
│       │   └── style.css       # HPTU-themed stylesheet (navy + gold)
│       └── js/
│           └── script.js       # Frontend logic (chat, filters, API calls)
│
├── assets/                     # Static assets (images, logos)
├── uploads/                    # User-uploaded PDFs (temporary)
└── data/
    └── notices.json            # Fallback notice data
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **MongoDB** (running locally or Atlas URI)
- **Cohere API Key** — [Get one here](https://dashboard.cohere.com/api-keys)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/burgerbeast7/HPTU-ASIST.git
   cd HPTU-AI-Assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux/Mac
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the root directory:
   ```env
   COHERE_API_KEY=your_cohere_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   GOOGLE_CSE_ID=your_google_custom_search_engine_id
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB_NAME=hptu_assistant
   SECRET_KEY=your-secret-key
   AUTO_SCRAPE_ENABLED=true
   SCRAPER_INTERVAL_MINUTES=30
   ```

5. **Start MongoDB**
   ```bash
   mongod
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

### Google Setup For Exact Date Answers (Optional but Recommended)

To enable live web search for exam dates and schedules:

1. **Create a Google Custom Search Engine**
   - Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Create a new search engine and add `himtu.ac.in` as the only searchable site
   - Note your **Search Engine ID**

2. **Enable Google Custom Search API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Search for "Custom Search API" and enable it
   - Create an API key (type: Browser key)

3. **Add to environment variables**
   ```env
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_search_engine_id
   ```

With this enabled, the chatbot will answer queries like:
- "When was HPCET exam 2026?"
- "When is the last date for admission HPTU 2026?"
- "What is the exam schedule for B.Tech 5th semester?"

**Note:** Without Google credentials, the system falls back to DuckDuckGo search for date queries.

---

## 🧪 Troubleshooting

- **Error: `ModuleNotFoundError: No module named 'cohere'`**
   Install dependencies again in the active virtual environment:
   ```bash
   pip install -r requirements.txt
   ```

- **PowerShell script execution issues (Windows)**
   If activation is blocked, run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   ```

- **App starts but page not opening**
   Make sure Flask is running and open:
   ```
   http://127.0.0.1:5000
   ```

---

## 🔑 Admin Access

| | |
|---|---|
| **URL** | `/admin/login` |
| **Username** | `` |
| **Password** | `` |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Home page |
| `/chat` | POST | Send message to AI chatbot |
| `/upload` | POST | Upload PDF for scanning |
| `/clear-pdf` | POST | Clear uploaded PDF context |
| `/api/hptu-notices` | GET | Get scraped HPTU notices |
| `/api/syllabus` | GET | Get syllabus data |
| `/api/fees` | GET | Get fee structure data |
| `/api/scraper-status` | GET | Get last scraper run status |
| `/api/scraped-pdfs` | GET | Get list of scanned PDFs |
| `/api/pyq/search` | GET | Search PYQ papers (`?q=&course=&branch=&semester=`) |
| `/api/pyq/courses` | GET | Get available PYQ courses and branches |
| `/admin/login` | GET/POST | Admin login |
| `/admin/dashboard` | GET | Admin dashboard |
| `/admin/trigger-scrape` | POST | Manually trigger scraper |

### Chat Commands for Results

Use these commands in the chat to retrieve exam results:

| Command | Example | Description |
|---|---|---|
| **Result by Roll** | `result 23015103036` | Fetch exam result by student roll number |
| **Result by Name** | `kunal chauhan` | Search exam result by student name (shows all matches) |
| **Date Query** | `when was hpcet exam 2026?` | Get exact exam date with sources (requires Google setup) |

---

## 🌐 Deployment (Render)

This project is configured for deployment on [Render](https://render.com):

1. Push your code to GitHub
2. Connect the repo on Render
3. Set environment variables in Render dashboard
4. The `Procfile` and `render.yaml` handle the rest

```
# Procfile
web: gunicorn run:app
```

---

## 📸 Screenshots

> _Add screenshots of your application here_

| Home Page | AI Chatbot | Admin Dashboard |
|---|---|---|
| ![Home](assets/home.png) | ![Chat](assets/chat.png) | ![Admin](assets/admin.png) |

---

## 🔮 Future Enhancements

- [ ] Multi-language support (Hindi + English)
- [x] Voice-based query input (Web Speech API)
- [x] PYQ system with structured data (course/branch/semester/subject)
- [x] Multi-page notice scraping from official HPTU site
- [ ] Push notifications for new notices
- [ ] Student login with personalized dashboard
- [ ] Integration with HPTU exam portal APIs
- [ ] Mobile app (React Native / Flutter)

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🙏 Acknowledgements

- **Himachal Pradesh Technical University (HPTU)** — for the official data source
- **Cohere** — for the AI language model API
- **HPTUOnline.com** — for previous year question papers
- **MongoDB** — for the database platform
- **Flask** — for the web framework

---

<p align="center">
  <strong>Made with ❤️ by Kunal Chauhan</strong><br>
  B.Tech CSE — Himachal Pradesh Technical University, Hamirpur<br>
  © 2026 All Rights Reserved
</p>
