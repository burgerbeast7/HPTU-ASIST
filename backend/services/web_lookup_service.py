"""
Web Lookup Service — live date/details lookup for HPTU exam timeline queries.
Uses Google Custom Search API when configured, with DuckDuckGo HTML fallback.
"""
import os
import re
from html import unescape
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 12

MONTHS_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", unescape(text or "")).strip()
    return cleaned


def _extract_year(text: str) -> str:
    m = re.search(r"\b(20\d{2})\b", text or "")
    return m.group(1) if m else ""


def _is_date_query(user_message: str) -> bool:
    msg = (user_message or "").lower()
    date_words = ["date", "when", "schedule", "exam", "hpcet", "admission", "deadline", "last date"]
    return any(w in msg for w in date_words)


def _google_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    cse_id = os.getenv("GOOGLE_CSE_ID", "").strip()
    if not api_key or not cse_id:
        return []

    try:
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": min(max(num_results, 1), 10),
        }
        resp = requests.get(GOOGLE_SEARCH_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("items", []):
            results.append(
                {
                    "title": _normalize_text(item.get("title", "")),
                    "link": item.get("link", ""),
                    "snippet": _normalize_text(item.get("snippet", "")),
                    "source": "google",
                }
            )
        return results
    except Exception as e:
        print(f"Google search lookup error: {e}")
        return []


def _duckduckgo_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Fallback when Google API is not configured."""
    try:
        resp = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for node in soup.select(".result"):
            a = node.select_one(".result__a")
            snippet = node.select_one(".result__snippet")
            if not a:
                continue
            link = a.get("href", "")
            if not link.startswith("http"):
                continue
            results.append(
                {
                    "title": _normalize_text(a.get_text(" ", strip=True)),
                    "link": link,
                    "snippet": _normalize_text(snippet.get_text(" ", strip=True) if snippet else ""),
                    "source": "duckduckgo",
                }
            )
            if len(results) >= num_results:
                break
        return results
    except Exception as e:
        print(f"Fallback search lookup error: {e}")
        return []


def _extract_candidate_lines(text: str, keyword: str = "") -> List[str]:
    lines = []
    normalized = _normalize_text(text)
    if not normalized:
        return lines

    # Split into sentence-like chunks.
    chunks = re.split(r"(?<=[.!?])\s+", normalized)
    keyword_l = (keyword or "").lower()
    for chunk in chunks:
        c = chunk.strip()
        if len(c) < 20:
            continue
        if keyword_l and keyword_l not in c.lower() and "exam" not in c.lower() and "hpcet" not in c.lower():
            continue
        lines.append(c)
    return lines[:30]


def _extract_dates(text: str) -> List[str]:
    patterns = [
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS_RE}\s+20\d{{2}}\b",
        rf"\b{MONTHS_RE}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+20\d{{2}}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]20\d{2}\b",
    ]
    found = []
    low = text.lower()
    for p in patterns:
        for m in re.finditer(p, low, re.IGNORECASE):
            found.append(text[m.start():m.end()])

    # De-dupe preserve order.
    out = []
    seen = set()
    for d in found:
        key = d.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _score_candidate_line(line: str, query: str, year: str = "") -> float:
    q = (query or "").lower()
    l = (line or "").lower()
    score = 0.0

    if "hpcet" in q and "hpcet" in l:
        score += 4.0
    if "exam" in l:
        score += 1.5
    if "date" in l or "held on" in l or "scheduled" in l:
        score += 1.5
    if year and year in l:
        score += 2.0

    for token in re.findall(r"[a-z0-9]+", q):
        if len(token) > 3 and token in l:
            score += 0.2
    return score


def _fetch_page_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style noise.
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return _normalize_text(soup.get_text(" ", strip=True))
    except Exception:
        return ""


def lookup_exact_date_details(user_message: str) -> Dict[str, str]:
    """
    Return exact date/details for exam/date timeline queries.
    Response shape:
      {ok: bool, answer: str, source: str, provider: str}
    """
    query = (user_message or "").strip()
    if not query or not _is_date_query(query):
        return {"ok": False, "reason": "not_date_query"}

    year = _extract_year(query)
    q = query
    if "site:" not in q.lower() and any(k in q.lower() for k in ["himtu", "hptu", "hpcet"]):
        q = f"{query} site:himtu.ac.in"

    search_results = _google_search(q, num_results=6)
    provider = "google"
    if not search_results:
        search_results = _duckduckgo_search(q, num_results=6)
        provider = "duckduckgo"

    if not search_results:
        return {
            "ok": False,
            "reason": "no_search_results",
            "fallback_link": "https://www.himtu.ac.in/en/admissions",
        }

    # Prefer official domains when available.
    def domain_score(link: str) -> int:
        l = (link or "").lower()
        if "himtu.ac.in" in l:
            return 3
        if "hptuexam.com" in l:
            return 2
        if "indiaresults.com" in l:
            return 1
        return 0

    search_results.sort(key=lambda r: domain_score(r.get("link", "")), reverse=True)

    best = None
    best_score = -1.0
    for res in search_results[:5]:
        page_text = _fetch_page_text(res.get("link", ""))
        combined_text = " ".join([res.get("title", ""), res.get("snippet", ""), page_text[:6000]])
        lines = _extract_candidate_lines(combined_text, keyword="hpcet" if "hpcet" in query.lower() else "exam")
        if not lines:
            lines = _extract_candidate_lines(combined_text)

        for line in lines:
            dates = _extract_dates(line)
            if not dates:
                continue
            score = _score_candidate_line(line, query, year=year)
            score += domain_score(res.get("link", ""))
            if score > best_score:
                best_score = score
                best = {
                    "date": dates[0],
                    "details": line,
                    "source": res.get("link", ""),
                    "title": res.get("title", ""),
                }

    if not best:
        top = search_results[0]
        return {
            "ok": False,
            "reason": "no_exact_date_found",
            "fallback_link": top.get("link", "https://www.himtu.ac.in/en/admissions"),
            "provider": provider,
        }

    answer = (
        f"Exact date: {best['date']}\n"
        f"Details: {best['details']}\n"
        f"Source: {best['source']}"
    )
    return {
        "ok": True,
        "answer": answer,
        "source": best["source"],
        "provider": provider,
        "title": best.get("title", ""),
    }
