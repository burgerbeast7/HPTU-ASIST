"""
PYQ Service — Scrape Previous Year Question Papers from hptuonline.com
Provides direct links to question papers organized by course, branch, and semester.
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.hptuonline.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# All courses with their page URLs
COURSES = {
    "btech": {
        "name": "B.Tech",
        "branches": {
            "first_year": {"name": "First Year (Common)", "url": f"{BASE_URL}/"},
            "cse_it": {"name": "CSE / IT", "url": f"{BASE_URL}/btech-cs-it-question-papers.html"},
            "civil": {"name": "Civil Engineering", "url": f"{BASE_URL}/btech-ce-question-papers.html"},
            "me": {"name": "Mechanical Engineering", "url": f"{BASE_URL}/btech-me-question-papers.html"},
            "e_all": {"name": "Electrical (All)", "url": f"{BASE_URL}/btech-e-question-papers.html"},
            "auto": {"name": "Automobile Engineering", "url": f"{BASE_URL}/btech-au-question-papers.html"},
            "te": {"name": "Textile Engineering", "url": f"{BASE_URL}/btech-te-question-papers.html"},
            "others": {"name": "Others", "url": f"{BASE_URL}/btech-others-question-papers.html"},
        }
    },
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


def _scrape_papers_from_page(url):
    """Scrape question paper links from a single page."""
    papers = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return papers

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all links that point to paper pages
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            title = link.get_text(strip=True)

            if not title or len(title) < 10:
                continue

            # Make URL absolute
            if not href.startswith("http"):
                if href.startswith("/"):
                    href = BASE_URL + href
                else:
                    href = BASE_URL + "/" + href

            # Filter for question paper links
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["sem", "semester", "paper", "exam", "question"]):
                papers.append({
                    "title": title.replace("-", " ").strip(),
                    "link": href,
                })

    except Exception as e:
        print(f"  PYQ scrape error ({url[:60]}): {e}")

    return papers


def scrape_all_pyq():
    """Scrape all PYQ data from hptuonline.com for every course and branch."""
    all_pyq = []

    for course_key, course_data in COURSES.items():
        course_name = course_data.get("name", course_key.upper())

        # B.Tech has branches
        if "branches" in course_data:
            for branch_key, branch_data in course_data["branches"].items():
                branch_name = branch_data["name"]
                branch_url = branch_data["url"]
                print(f"  📝 Scraping PYQ: {course_name} - {branch_name}...")

                papers = _scrape_papers_from_page(branch_url)
                for paper in papers:
                    paper["course"] = course_name
                    paper["branch"] = branch_name
                    paper["source"] = "hptuonline.com"
                    all_pyq.append(paper)
        else:
            # Other courses (single page)
            course_url = course_data.get("url", "")
            if course_url:
                print(f"  📝 Scraping PYQ: {course_name}...")
                papers = _scrape_papers_from_page(course_url)
                for paper in papers:
                    paper["course"] = course_name
                    paper["branch"] = ""
                    paper["source"] = "hptuonline.com"
                    all_pyq.append(paper)

    print(f"  ✅ Total PYQ papers scraped: {len(all_pyq)}")
    return all_pyq


def search_pyq(query):
    """Search PYQ papers from MongoDB by keyword."""
    from backend.services.notice_service import load_pyq

    query_lower = query.lower()
    results = []
    all_papers = load_pyq()

    for paper in all_papers:
        title = paper.get("title", "").lower()
        course = paper.get("course", "").lower()
        branch = paper.get("branch", "").lower()

        if (query_lower in title or query_lower in course or query_lower in branch):
            results.append(paper)

    return results
