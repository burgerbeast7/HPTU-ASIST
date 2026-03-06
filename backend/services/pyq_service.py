"""
PYQ Service — Scrape Previous Year Question Papers from hptuonline.com
Provides direct links to question papers organized by course, branch, semester, and subject.
"""
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.hptuonline.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# All courses with their page URLs
BTECH_BRANCHES = {
    "first_year": {"name": "First Year (Common)", "url": f"{BASE_URL}/"},
    "cse_it": {"name": "CSE / IT", "url": f"{BASE_URL}/btech-cs-it-question-papers.html"},
    "civil": {"name": "Civil Engineering", "url": f"{BASE_URL}/btech-ce-question-papers.html"},
    "me": {"name": "Mechanical Engineering", "url": f"{BASE_URL}/btech-me-question-papers.html"},
    "e_all": {"name": "Electrical (All)", "url": f"{BASE_URL}/btech-e-question-papers.html"},
    "auto": {"name": "Automobile Engineering", "url": f"{BASE_URL}/btech-au-question-papers.html"},
    "te": {"name": "Textile Engineering", "url": f"{BASE_URL}/btech-te-question-papers.html"},
    "others": {"name": "Others", "url": f"{BASE_URL}/btech-others-question-papers.html"},
}

OTHER_COURSES = {
    "bba": {"name": "BBA", "url": f"{BASE_URL}/bba.html"},
    "bca": {"name": "BCA", "url": f"{BASE_URL}/bca.html"},
    "bhmct": {"name": "BHMCT", "url": f"{BASE_URL}/bhmct.html"},
    "bpharmacy": {"name": "B.Pharmacy", "url": f"{BASE_URL}/bpharmacy.html"},
    "mba": {"name": "MBA", "url": f"{BASE_URL}/mba.html"},
    "mca": {"name": "MCA", "url": f"{BASE_URL}/mca.html"},
    "mpharmacy": {"name": "M.Pharmacy", "url": f"{BASE_URL}/mpharmacy.html"},
    "msc": {"name": "M.Sc", "url": f"{BASE_URL}/msc.html"},
    "mtech": {"name": "M.Tech", "url": f"{BASE_URL}/mtech.html"},
    "phd": {"name": "Ph.D", "url": f"{BASE_URL}/phd.html"},
    "yoga": {"name": "Yoga", "url": f"{BASE_URL}/yoga.html"},
    "hptsb_diploma": {"name": "HPTSB Diploma", "url": f"{BASE_URL}/hptsb-diploma.html"},
    "hptsb_iti": {"name": "HPTSB ITI", "url": f"{BASE_URL}/hptsb-iti.html"},
}


def _parse_paper_title(raw_title):
    """Parse a paper title like 'BTECH-CS-AILM-AIDS-3-SEM-DATA-STRUCTURES-0098-DEC-2024'
    into structured data: subject name, semester, exam month/year, code."""
    title = raw_title.replace("-", " ").strip()

    # Extract semester (handles both "3 SEM" and "3-SEM")
    sem_match = re.search(r'(\d+)[-\s]*SEM', raw_title, re.IGNORECASE)
    semester = int(sem_match.group(1)) if sem_match else 0

    # Extract exam month and year (e.g., DEC-2024, MAY-2024, JUL-2023)
    exam_match = re.search(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[-\s]*(\d{4})', raw_title, re.IGNORECASE)
    exam_period = f"{exam_match.group(1).title()} {exam_match.group(2)}" if exam_match else ""

    # Extract code (4-digit number before the month, like 0098-DEC)
    code_match = re.search(r'(\d{4})[-\s]*(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', raw_title, re.IGNORECASE)
    code = code_match.group(1) if code_match else ""

    # Extract subject name: remove course prefix, semester, code, month/year
    subject = raw_title
    # Remove BTECH prefix with all branch codes (greedy, multiple codes)
    # NOTE: longer alternatives like EEE must come before EE to avoid partial matching
    subject = re.sub(r'^BTECH(?:[-\s]+(?:AILM|AIDS|AUTO|CIVIL|CSE|ECE|EEE|EE|EX|CS|CE|IT|ME|AU|TE))*[-\s]*', '', subject, flags=re.IGNORECASE)
    # Remove other course prefixes
    subject = re.sub(r'^(?:BBA|BCA|MBA|MCA|BHMCT|BPHARMACY|MPHARMACY|MSC|MTECH|PHD|YOGA)[-\s]*', '', subject, flags=re.IGNORECASE)
    # Remove semester part
    subject = re.sub(r'\d+[-\s]*SEM[-\s]*', '', subject, flags=re.IGNORECASE)
    # Remove code and date at end (e.g., -0098-DEC-2024)
    subject = re.sub(r'[-\s]*\d{4}[-\s]*(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[-\s]*\d{4}[-\s]*$', '', subject, flags=re.IGNORECASE)
    # Also remove trailing code without month
    subject = re.sub(r'[-\s]*\d{4,6}[-\s]*$', '', subject, flags=re.IGNORECASE)
    # Remove scheme identifiers
    subject = re.sub(r'[-\s]*(?:NS|OS|CBCS|J|FB|D|C|M|A)[-\s]*\d{5,6}[-\s]*(?:\d{4})?[-\s]*$', '', subject, flags=re.IGNORECASE)
    # Clean up
    subject = subject.replace("-", " ").strip()
    subject = re.sub(r'\s+', ' ', subject)

    return {
        "subject": subject.title() if subject else title.title(),
        "semester": semester,
        "exam_period": exam_period,
        "code": code,
    }


def _scrape_papers_from_page(url):
    """Scrape question paper links from a single page, grouped by semester."""
    papers = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return papers

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find current semester heading context
        current_semester_heading = ""

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            raw_title = a.get_text(strip=True)

            # Only process paper links
            if "/papers/" not in href:
                continue
            if not raw_title or len(raw_title) < 10:
                continue

            # Make URL absolute
            if not href.startswith("http"):
                href = BASE_URL + "/" + href.lstrip("/")

            # Parse structured data from title
            parsed = _parse_paper_title(raw_title)

            papers.append({
                "title": raw_title.replace("-", " ").strip(),
                "subject": parsed["subject"],
                "semester": parsed["semester"],
                "exam_period": parsed["exam_period"],
                "code": parsed["code"],
                "link": href,
            })

    except Exception as e:
        print(f"  PYQ scrape error ({url[:60]}): {e}")

    return papers


def scrape_all_pyq():
    """Scrape all PYQ data from hptuonline.com for every course and branch."""
    all_pyq = []

    # B.Tech branches
    for branch_key, branch_data in BTECH_BRANCHES.items():
        branch_name = branch_data["name"]
        branch_url = branch_data["url"]
        print(f"  📝 Scraping PYQ: B.Tech - {branch_name}...")

        papers = _scrape_papers_from_page(branch_url)
        for paper in papers:
            paper["course"] = "B.Tech"
            paper["branch"] = branch_name
            paper["source"] = "hptuonline.com"
            all_pyq.append(paper)

    # Other courses
    for course_key, course_data in OTHER_COURSES.items():
        course_name = course_data["name"]
        course_url = course_data["url"]
        print(f"  📝 Scraping PYQ: {course_name}...")

        papers = _scrape_papers_from_page(course_url)
        for paper in papers:
            paper["course"] = course_name
            paper["branch"] = ""
            paper["source"] = "hptuonline.com"
            all_pyq.append(paper)

    print(f"  ✅ Total PYQ papers scraped: {len(all_pyq)}")
    return all_pyq


def get_available_courses():
    """Return list of available courses for PYQ."""
    courses = ["B.Tech"]
    courses += [c["name"] for c in OTHER_COURSES.values()]
    return courses


def get_btech_branches():
    """Return list of B.Tech branches."""
    return [b["name"] for b in BTECH_BRANCHES.values()]


def get_available_semesters(course, branch=""):
    """Return available semesters for a course/branch from scraped data."""
    from backend.services.notice_service import load_pyq
    all_papers = load_pyq()

    semesters = set()
    for paper in all_papers:
        if paper.get("course", "").lower() == course.lower():
            if branch and paper.get("branch", "").lower() != branch.lower():
                continue
            sem = paper.get("semester", 0)
            if sem > 0:
                semesters.add(sem)

    return sorted(semesters)


def search_pyq(query, course="", branch="", semester=0):
    """Search PYQ papers with optional filters."""
    from backend.services.notice_service import load_pyq

    query_lower = query.lower()
    results = []
    all_papers = load_pyq()

    for paper in all_papers:
        # Apply filters
        if course and paper.get("course", "").lower() != course.lower():
            continue
        if branch and branch.lower() not in paper.get("branch", "").lower():
            continue
        if semester and paper.get("semester", 0) != semester:
            continue

        # Keyword search
        title = paper.get("title", "").lower()
        subject = paper.get("subject", "").lower()
        p_course = paper.get("course", "").lower()
        p_branch = paper.get("branch", "").lower()

        searchable = f"{title} {subject} {p_course} {p_branch}"
        if not query_lower or any(w in searchable for w in query_lower.split()):
            results.append(paper)

    return results
