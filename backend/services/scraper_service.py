"""
Scraper Service — Scrape notices from the official HPTU website
"""
import requests
from bs4 import BeautifulSoup


def scrape_hptu_notices():
    """Scrape latest notifications from the official HPTU website."""
    notices = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://www.himtu.ac.in/notice-board"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # The notice board page uses a table with rows
        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select("table tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            title = cells[0].get_text(strip=True)
            if not title:
                continue

            date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            last_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""

            # Find document download link
            doc_link = ""
            for cell in cells:
                link_tag = cell.find("a", href=True)
                if link_tag:
                    href = link_tag["href"]
                    if href.startswith("/"):
                        href = "https://www.himtu.ac.in" + href
                    if href.endswith(".pdf") or "default/files" in href or href.startswith("http"):
                        doc_link = href
                        break

            notices.append({
                "title": title,
                "date": date,
                "last_date": last_date,
                "link": doc_link,
                "source": "hptu_official"
            })

        # Fallback: try scraping from the home page "What's New" ticker
        if not notices:
            home_resp = requests.get("https://www.himtu.ac.in/", headers=headers, timeout=15)
            home_soup = BeautifulSoup(home_resp.text, "html.parser")
            ticker_links = home_soup.select(
                '.marquee-content a, .whats-new a, [class*="ticker"] a, [class*="notification"] a'
            )
            for link in ticker_links[:20]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if title and len(title) > 10:
                    if href.startswith("/"):
                        href = "https://www.himtu.ac.in" + href
                    notices.append({
                        "title": title,
                        "date": "",
                        "last_date": "",
                        "link": href,
                        "source": "hptu_official"
                    })

    except Exception as e:
        print(f"HPTU Scrape Error: {e}")

    return notices
