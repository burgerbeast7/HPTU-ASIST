"""
Scraper Service — Comprehensive HPTU website scraper
Scrapes: notices, PDFs (with text extraction), syllabus, fees, exam info
Auto-downloads and extracts text from PDF notifications.
"""
import io
import re
import traceback
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://www.himtu.ac.in"


def _make_absolute(href):
    """Convert relative URLs to absolute."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def _extract_pdf_text_from_url(url, max_pages=10):
    """Download a PDF from URL and extract its text content."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return ""

        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(resp.content))
        text = ""
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"  PDF extract error ({url[:60]}...): {e}")
        return ""


def _categorize_notice(title):
    """Auto-categorize a notice based on its title."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["exam", "date sheet", "datesheet", "result", "revaluation", "re-evaluation"]):
        return "examination"
    if any(w in title_lower for w in ["admission", "admit", "hpcet", "entrance", "counseling", "counselling"]):
        return "admission"
    if any(w in title_lower for w in ["syllabus", "curriculum", "scheme", "course"]):
        return "syllabus"
    if any(w in title_lower for w in ["fee", "fees", "payment", "scholarship", "refund"]):
        return "fees"
    if any(w in title_lower for w in ["recruitment", "faculty", "staff", "vacancy", "hiring"]):
        return "recruitment"
    if any(w in title_lower for w in ["convocation", "degree", "certificate"]):
        return "convocation"
    return "general"


# ─── Main Scraper Functions ──────────────────────

def scrape_hptu_notices():
    """Scrape latest notifications from the official HPTU website notice board."""
    notices = []
    try:
        url = f"{BASE_URL}/notice-board"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select("table tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            title = cells[0].get_text(strip=True)
            if not title or len(title) < 5:
                continue

            date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            last_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""

            doc_link = ""
            for cell in cells:
                link_tag = cell.find("a", href=True)
                if link_tag:
                    href = link_tag["href"]
                    href = _make_absolute(href)
                    if href.endswith(".pdf") or "default/files" in href or href.startswith("http"):
                        doc_link = href
                        break

            notices.append({
                "title": title,
                "date": date,
                "last_date": last_date,
                "link": doc_link,
                "source": "hptu_official",
                "category": _categorize_notice(title),
                "pdf_text": "",
            })

        # Fallback: try the home page ticker
        if not notices:
            home_resp = requests.get(f"{BASE_URL}/", headers=HEADERS, timeout=15)
            home_soup = BeautifulSoup(home_resp.text, "html.parser")
            ticker_links = home_soup.select(
                '.marquee-content a, .whats-new a, [class*="ticker"] a, [class*="notification"] a'
            )
            for link in ticker_links[:30]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if title and len(title) > 10:
                    href = _make_absolute(href)
                    notices.append({
                        "title": title,
                        "date": "",
                        "last_date": "",
                        "link": href,
                        "source": "hptu_official",
                        "category": _categorize_notice(title),
                        "pdf_text": "",
                    })

    except Exception as e:
        print(f"HPTU Scrape Error: {e}")

    return notices


def scrape_hptu_syllabus():
    """Scrape syllabus/curriculum data from HPTU website."""
    syllabus_items = []
    try:
        # Try common syllabus pages
        syllabus_urls = [
            f"{BASE_URL}/syllabus",
            f"{BASE_URL}/curriculum",
            f"{BASE_URL}/scheme-syllabus",
        ]
        for url in syllabus_urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for PDF links related to syllabus
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    href = _make_absolute(href)
                    if href.endswith(".pdf") or "syllabus" in href.lower() or "scheme" in href.lower():
                        syllabus_items.append({
                            "title": title,
                            "link": href,
                            "program": _detect_program(title),
                            "source": "hptu_official",
                        })
                if syllabus_items:
                    break
            except Exception:
                continue

        # Also extract syllabus-related items from notice board
        notices = scrape_hptu_notices()
        for notice in notices:
            if notice.get("category") == "syllabus":
                syllabus_items.append({
                    "title": notice["title"],
                    "link": notice.get("link", ""),
                    "program": _detect_program(notice["title"]),
                    "date": notice.get("date", ""),
                    "source": "hptu_notice_board",
                })

    except Exception as e:
        print(f"Syllabus scrape error: {e}")

    return syllabus_items


def scrape_hptu_fees():
    """Scrape fee structure data from HPTU website."""
    fees_items = []
    try:
        fee_urls = [
            f"{BASE_URL}/fee-structure",
            f"{BASE_URL}/fees",
            f"{BASE_URL}/fee",
        ]
        for url in fee_urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")

                # Parse tables for fee data
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            text = " | ".join(c.get_text(strip=True) for c in cells)
                            if text and len(text) > 10:
                                fees_items.append({
                                    "description": text,
                                    "source": "hptu_official",
                                })

                # Also look for PDF links
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    if title and ("fee" in title.lower() or "fee" in href.lower()):
                        href = _make_absolute(href)
                        fees_items.append({
                            "title": title,
                            "link": href,
                            "source": "hptu_official",
                        })
                if fees_items:
                    break
            except Exception:
                continue

        # Also extract fee-related items from notices
        notices = scrape_hptu_notices()
        for notice in notices:
            if notice.get("category") == "fees":
                fees_items.append({
                    "title": notice["title"],
                    "link": notice.get("link", ""),
                    "date": notice.get("date", ""),
                    "source": "hptu_notice_board",
                })

    except Exception as e:
        print(f"Fees scrape error: {e}")

    return fees_items


def scrape_hptu_documents():
    """Scrape important documents/PDFs from multiple HPTU pages (examination, academics, student-zone, forms, circulars)."""
    documents = []
    seen_urls = set()

    # Pages to scrape for documents
    doc_pages = [
        (f"{BASE_URL}/en/examination", "examination"),
        (f"{BASE_URL}/en/examination/examination-schedule", "examination"),
        (f"{BASE_URL}/acadmeics", "academics"),
        (f"{BASE_URL}/en/student-zone/forms", "forms"),
        (f"{BASE_URL}/en/information-corner/circulars-notices", "circulars"),
        (f"{BASE_URL}/en/admissions", "admission"),
        (f"{BASE_URL}/notice-board", "notice"),
        (f"{BASE_URL}/en/student-zone", "student"),
    ]

    for page_url, doc_type in doc_pages:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract all links from the page
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                href = _make_absolute(href)

                # Skip navigation/menu links, keep document links
                is_doc = (
                    href.endswith(".pdf") or
                    href.endswith(".docx") or
                    href.endswith(".doc") or
                    "default/files" in href or
                    "hptuexam.com" in href or
                    "indiaresults.com" in href or
                    "sbicollect" in href
                )
                if not is_doc:
                    continue

                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Determine document category
                category = _categorize_document(title, href, doc_type)

                documents.append({
                    "title": title,
                    "link": href,
                    "type": doc_type,
                    "category": category,
                    "program": _detect_program(title),
                    "source_page": page_url,
                })

            # Also extract from tables (date sheets etc.)
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    row_title = cells[0].get_text(strip=True)
                    if not row_title or len(row_title) < 5:
                        continue
                    for cell in cells:
                        cell_link = cell.find("a", href=True)
                        if cell_link:
                            href = _make_absolute(cell_link["href"])
                            if href in seen_urls:
                                continue
                            seen_urls.add(href)
                            category = _categorize_document(row_title, href, doc_type)
                            documents.append({
                                "title": row_title,
                                "link": href,
                                "type": doc_type,
                                "category": category,
                                "program": _detect_program(row_title),
                                "source_page": page_url,
                            })
        except Exception as e:
            print(f"  Doc scrape error ({page_url}): {e}")

    # Add well-known HPTU resource links
    static_docs = [
        {"title": "HPTU Examination Portal - Admit Cards & Forms", "link": "https://hptuexam.com/", "category": "examination_portal", "type": "portal"},
        {"title": "HPTU Results - Check All Results", "link": "https://himachal-pradesh.indiaresults.com/himtu/default.aspx", "category": "results", "type": "portal"},
        {"title": "HPTU Online Fee Payment (SBI Collect)", "link": "https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?corpID=2471557", "category": "fee_payment", "type": "portal"},
        {"title": "HPTU Notice Board - All Notifications", "link": f"{BASE_URL}/notice-board", "category": "notices", "type": "portal"},
        {"title": "HPTU Examination Schedule", "link": f"{BASE_URL}/en/examination/examination-schedule", "category": "date_sheet", "type": "portal"},
        {"title": "HPTU Student Related Forms (Download)", "link": f"{BASE_URL}/en/student-zone/forms", "category": "forms", "type": "portal"},
        {"title": "HPTU DigiLocker - Download Certificates", "link": "https://nad.digilocker.gov.in/", "category": "certificates", "type": "portal"},
        {"title": "HPTU Admission Information", "link": f"{BASE_URL}/en/admissions", "category": "admission", "type": "portal"},
        {"title": "HPTU Official Website", "link": BASE_URL, "category": "general", "type": "portal"},
        {"title": "HPTU Contact Us", "link": f"{BASE_URL}/en/contact-us", "category": "general", "type": "portal"},
    ]
    for doc in static_docs:
        doc["program"] = "General"
        doc["source_page"] = "static"
        documents.append(doc)

    return documents


def _categorize_document(title, href, page_type):
    """Categorize a document based on its title, URL, and source page."""
    t = title.lower()
    h = href.lower()

    if any(w in t for w in ["academic calendar", "calendar"]):
        return "academic_calendar"
    if any(w in t for w in ["date sheet", "datesheet", "date-sheet"]):
        return "date_sheet"
    if any(w in t for w in ["admit card", "hall ticket"]):
        return "admit_card"
    if any(w in t for w in ["result", "marksheet", "mark sheet"]):
        return "results"
    if any(w in t for w in ["syllabus", "curriculum", "scheme"]):
        return "syllabus"
    if any(w in t for w in ["fee", "payment"]):
        return "fees"
    if any(w in t for w in ["form", "application", "proforma"]):
        return "forms"
    if any(w in t for w in ["admission", "counseling", "counselling", "hpcet", "entrance"]):
        return "admission"
    if any(w in t for w in ["circular", "ordinance", "regulation", "statute"]):
        return "circulars"
    if any(w in t for w in ["tender", "quotation"]):
        return "tender"
    if any(w in t for w in ["revaluation", "re-evaluation", "rechecking"]):
        return "revaluation"
    if any(w in t for w in ["special chance", "re-appear", "reappear", "back paper"]):
        return "special_chance"
    if any(w in t for w in ["holiday", "vacation"]):
        return "holiday_calendar"
    if "pdf" in h or "default/files" in h:
        return page_type
    return "general"


def _detect_program(title):
    """Detect academic program from title text."""
    title_lower = title.lower()
    programs = {
        "B.Tech": ["b.tech", "btech", "b tech"],
        "M.Tech": ["m.tech", "mtech", "m tech"],
        "MBA": ["mba", "m.b.a"],
        "BBA": ["bba", "b.b.a"],
        "MCA": ["mca", "m.c.a"],
        "BCA": ["bca", "b.c.a"],
        "B.Pharmacy": ["b.pharm", "bpharm", "b pharmacy", "b.pharmacy"],
        "M.Pharmacy": ["m.pharm", "mpharm", "m pharmacy", "m.pharmacy"],
        "Diploma": ["diploma"],
        "Ph.D": ["phd", "ph.d", "doctoral"],
    }
    for prog, keywords in programs.items():
        for kw in keywords:
            if kw in title_lower:
                return prog
    return "General"


def scan_pdf_notices(notices, max_pdfs=20):
    """Download and extract text from PDF notices. Returns updated notices with pdf_text."""
    scanned_count = 0
    from backend.services.notice_service import save_scraped_pdf

    for notice in notices:
        if scanned_count >= max_pdfs:
            break
        link = notice.get("link", "")
        if not link or not (link.endswith(".pdf") or "default/files" in link):
            continue

        print(f"  📄 Scanning PDF: {notice.get('title', '')[:50]}...")
        text = _extract_pdf_text_from_url(link)
        if text:
            notice["pdf_text"] = text[:5000]  # Store first 5000 chars
            save_scraped_pdf({
                "url": link,
                "title": notice.get("title", ""),
                "text": text[:10000],
                "category": notice.get("category", "general"),
            })
            scanned_count += 1

    return notices, scanned_count


def run_full_scrape():
    """Run a comprehensive scrape of all HPTU data and store in MongoDB."""
    from backend.services.notice_service import (
        save_hptu_notices, save_syllabus, save_fees, save_scraper_status, save_documents, save_pyq
    )

    status = {
        "key": "last_run",
        "status": "running",
        "last_run": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "notices_count": 0,
        "pdfs_scanned": 0,
        "syllabus_count": 0,
        "fees_count": 0,
        "documents_count": 0,
        "pyq_count": 0,
    }

    try:
        # 1. Scrape notices
        print("📋 Scraping HPTU notices...")
        notices = scrape_hptu_notices()
        status["notices_count"] = len(notices)

        # 2. Scan PDFs from notices
        print("📄 Scanning PDFs from notices...")
        notices, pdf_count = scan_pdf_notices(notices, max_pdfs=15)
        status["pdfs_scanned"] = pdf_count

        # 3. Save notices with PDF text
        save_hptu_notices(notices)

        # 4. Scrape syllabus
        print("📚 Scraping syllabus data...")
        syllabus = scrape_hptu_syllabus()
        status["syllabus_count"] = len(syllabus)
        if syllabus:
            save_syllabus(syllabus)

        # 5. Scrape fees
        print("💰 Scraping fees data...")
        fees = scrape_hptu_fees()
        status["fees_count"] = len(fees)
        if fees:
            save_fees(fees)

        # 6. Scrape documents from all important pages
        print("📂 Scraping documents & resources...")
        documents = scrape_hptu_documents()
        status["documents_count"] = len(documents)
        if documents:
            save_documents(documents)

        # 7. Scrape PYQ from hptuonline.com
        print("📝 Scraping Previous Year Questions (PYQ)...")
        from backend.services.pyq_service import scrape_all_pyq
        pyq_papers = scrape_all_pyq()
        status["pyq_count"] = len(pyq_papers)
        if pyq_papers:
            save_pyq(pyq_papers)

        status["status"] = "success"
        print(f"✅ Full scrape complete: {len(notices)} notices, {pdf_count} PDFs, "
              f"{len(syllabus)} syllabus, {len(fees)} fees, {len(documents)} documents, "
              f"{len(pyq_papers)} PYQ papers")

    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)
        print(f"❌ Full scrape error: {e}")
        traceback.print_exc()

    save_scraper_status(status)
    return status
