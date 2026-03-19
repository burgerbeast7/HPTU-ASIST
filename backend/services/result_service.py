"""
Result Service — B.Tech 5th semester result lookup from IndiaResults.
Handles roll number submission and lightweight parsing of the result page.
"""
import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


DESKTOP_QUERY_URL = "https://himturesult.indiaresults.com/hp/himtu/hp-himtu/query.aspx?id=1800266731"
MOBILE_QUERY_URL = "https://results.indiaresults.com/hp/himtu/hp-himtu/mquery.aspx?id=1800266731"
MOBILE_RESULT_POST_URL = "https://results.indiaresults.com/hp/himtu/mresult.aspx"
DESKTOP_NAME_RESULT_POST_URL = "https://himturesult.indiaresults.com/hp/himtu/name-results.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": MOBILE_QUERY_URL,
}


def _extract_hidden_fields(query_html: str) -> Dict[str, str]:
    """Extract required hidden ASP.NET fields from the query page."""
    soup = BeautifulSoup(query_html, "html.parser")
    form = soup.find("form", id="frm1") or soup.find("form")
    if not form:
        return {}

    fields = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        if name in {"__VIEWSTATE", "__VIEWSTATEGENERATOR", "id"}:
            fields[name] = inp.get("value", "")
    return fields


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_key_values(result_container: BeautifulSoup) -> Dict[str, str]:
    """Extract key/value fields from result table rows when available."""
    kv: Dict[str, str] = {}
    skip_keys = {
        "search another roll no.", "print this page", "<<back", "back",
    }

    for tr in result_container.find_all("tr"):
        cells = [
            _normalize_space(td.get_text(" ", strip=True))
            for td in tr.find_all(["td", "th"])
        ]
        cells = [c for c in cells if c]
        if len(cells) != 2:
            continue

        key = cells[0].strip(" :").lower()
        value = cells[1].strip()
        if not key or not value:
            continue
        if key in skip_keys:
            continue
        if len(key) > 45:
            continue
        kv[key] = value

    return kv


def _extract_key_values_from_text(visible_text: str) -> Dict[str, str]:
    """Fallback extraction for pages where labels are rendered as plain text blocks."""
    out: Dict[str, str] = {}
    text = visible_text or ""

    patterns = {
        "name": [r"(?:candidate\s*name|student\s*name|name)\s*[:\-]\s*([A-Za-z\s\.]+)"],
        "roll no": [r"(?:roll\s*no\.?|roll\s*number)\s*[:\-]\s*(\d{5,15})"],
        "result": [r"(?:final\s*result|result|status)\s*[:\-]\s*([A-Za-z\s\+\-]+)"],
        "sgpa": [r"sgpa\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)"],
        "cgpa": [r"cgpa\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)"],
    }

    for key, regex_list in patterns.items():
        for rgx in regex_list:
            m = re.search(rgx, text, re.IGNORECASE)
            if m:
                out[key] = _normalize_space(m.group(1))
                break

    if "result" not in out:
        # Loose fallback for explicit PASS/FAIL mentions.
        m = re.search(r"\b(pass|passed|fail|failed|re-appear|reappear)\b", text, re.IGNORECASE)
        if m:
            out["result"] = m.group(1).upper()

    return out


def _extract_subject_rows(result_container: BeautifulSoup) -> List[str]:
    """Extract subject-wise rows (best effort)."""
    subject_lines: List[str] = []
    subject_words = (
        "subject", "code", "marks", "grade", "credit", "obtained", "total", "theory", "practical"
    )

    for tr in result_container.find_all("tr"):
        cells = [
            _normalize_space(td.get_text(" ", strip=True))
            for td in tr.find_all(["td", "th"])
        ]
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue

        row_text = " | ".join(cells)
        row_l = row_text.lower()
        if "search another" in row_l or "print this page" in row_l:
            continue
        # Skip obvious header/utility rows
        if any(k in row_l for k in ["disclaimer", "indiaresults", "back"]):
            continue
        # Keep rows that look like academic table rows.
        looks_structured = any(w in row_l for w in subject_words) or re.search(r"\b[A-Z]{2,}\-?\d{2,4}\b", row_text) is not None
        if len(row_text) > 8 and looks_structured:
            subject_lines.append(row_text)

    # De-duplicate while preserving order
    deduped: List[str] = []
    seen = set()
    for line in subject_lines:
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)
    return deduped


def _extract_name_from_message(user_message: str) -> str:
    """Best-effort extraction of candidate name from user message."""
    msg = _normalize_space(user_message)
    if not msg:
        return ""

    patterns = [
        r"(?:my\s+name\s+is|name\s+is|name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.'-]{1,60})",
        r"(?:search\s+result\s+for|result\s+for)\s+([A-Za-z][A-Za-z\s\.'-]{1,60})",
    ]
    for rgx in patterns:
        m = re.search(rgx, msg, re.IGNORECASE)
        if m:
            name = _normalize_space(m.group(1))
            # Trim known tail words.
            name = re.sub(r"\b(result|roll|number|btech|semester|sem|please|check)\b.*$", "", name, flags=re.IGNORECASE).strip()
            if len(name) >= 2:
                return name

    # Fallback: strip common command words and keep alphabetic phrase.
    cleaned = re.sub(r"\b(check|show|search|find|my|for|the|result|results|btech|semester|sem|roll|number|of)\b", " ", msg, flags=re.IGNORECASE)
    cleaned = _normalize_space(cleaned)
    if re.fullmatch(r"[A-Za-z\s\.'-]{2,60}", cleaned):
        return cleaned
    return ""


def _extract_name_candidates(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Parse candidate list from name-results page (best effort)."""
    candidates: List[Dict[str, str]] = []

    # Primary selector used by IndiaResults pages.
    buttons = soup.select(".gv_button[data-prop], input.gv_button[data-prop], a.gv_button[data-prop], button.gv_button[data-prop]")
    for btn in buttons:
        roll = _normalize_space(btn.get("data-prop", ""))
        if not re.fullmatch(r"\d{5,15}", roll):
            continue

        tr = btn.find_parent("tr")
        row_text = _normalize_space(tr.get_text(" ", strip=True) if tr else "")
        cells = [_normalize_space(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"]) if _normalize_space(td.get_text(" ", strip=True))] if tr else []

        # Guess candidate name from row cells.
        name_guess = ""
        for c in cells:
            lc = c.lower()
            if c == roll:
                continue
            if re.fullmatch(r"\d+", c):
                continue
            if any(k in lc for k in ["show", "result", "click", "view"]):
                continue
            if re.search(r"[A-Za-z]", c):
                name_guess = c
                break

        candidates.append({
            "roll_no": roll,
            "name": name_guess,
            "row": row_text,
        })

    # Secondary fallback: parse rows containing roll numbers.
    if not candidates:
        for tr in soup.find_all("tr"):
            cells = [_normalize_space(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            rolls = [c for c in cells if re.fullmatch(r"\d{5,15}", c)]
            if not rolls:
                continue
            roll = rolls[0]
            name_guess = ""
            for c in cells:
                lc = c.lower()
                if c == roll or re.fullmatch(r"\d+", c):
                    continue
                if any(k in lc for k in ["show", "result", "click", "view", "roll"]):
                    continue
                if re.search(r"[A-Za-z]", c):
                    name_guess = c
                    break
            candidates.append({
                "roll_no": roll,
                "name": name_guess,
                "row": " | ".join(cells),
            })

    # De-duplicate by roll no
    dedup = {}
    for item in candidates:
        roll = item.get("roll_no", "")
        if roll and roll not in dedup:
            dedup[roll] = item
    return list(dedup.values())


def fetch_btech_5th_results_by_name(name: str) -> Dict[str, object]:
    """Search B.Tech 5th sem results by candidate name and return matching roll numbers."""
    name = _normalize_space(name)
    if not re.fullmatch(r"[A-Za-z\s\.'-]{2,60}", name):
        return {
            "ok": False,
            "status": "invalid_name",
            "message": "Please enter a valid name to search results.",
            "source": DESKTOP_QUERY_URL,
        }

    try:
        session = requests.Session()
        query_resp = session.get(DESKTOP_QUERY_URL, headers=HEADERS, timeout=20)
        query_resp.raise_for_status()

        query_soup = BeautifulSoup(query_resp.text, "html.parser")
        query_title = _normalize_space(query_soup.title.get_text(" ", strip=True) if query_soup.title else "")
        if query_title and ("5th semester" not in query_title.lower() or "b.tech" not in query_title.lower()):
            return {
                "ok": False,
                "status": "wrong_exam_page",
                "message": "Only B.Tech 5th semester result is available right now.",
                "source": DESKTOP_QUERY_URL,
            }

        payload = _extract_hidden_fields(query_resp.text)
        payload["txtName"] = name

        resp = session.post(DESKTOP_NAME_RESULT_POST_URL, data=payload, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        candidates = _extract_name_candidates(soup)
        if not candidates:
            return {
                "ok": False,
                "status": "not_found_name",
                "message": f"No B.Tech 5th sem result found for name '{name}'.",
                "exam": query_title,
                "source": DESKTOP_QUERY_URL,
            }

        return {
            "ok": True,
            "status": "found_name",
            "exam": query_title,
            "search_name": name,
            "matches": candidates[:15],
            "source": DESKTOP_QUERY_URL,
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status": "network_error",
            "message": f"Could not fetch result portal right now: {e}",
            "source": DESKTOP_QUERY_URL,
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "parse_error",
            "message": f"Could not parse name search result right now: {e}",
            "source": DESKTOP_QUERY_URL,
        }


def fetch_btech_5th_result(roll_no: str) -> Dict[str, object]:
    """
    Fetch B.Tech 5th semester result for a given roll number.
    Returns a dict with status and parsed data.
    """
    roll_no = _normalize_space(roll_no)
    if not re.fullmatch(r"\d{5,15}", roll_no):
        return {
            "ok": False,
            "status": "invalid_roll",
            "message": "Please enter a valid numeric roll number.",
        }

    try:
        session = requests.Session()
        query_resp = session.get(MOBILE_QUERY_URL, headers=HEADERS, timeout=20)
        query_resp.raise_for_status()

        query_soup = BeautifulSoup(query_resp.text, "html.parser")
        query_title = _normalize_space(query_soup.title.get_text(" ", strip=True) if query_soup.title else "")

        payload = _extract_hidden_fields(query_resp.text)
        payload["RollNo"] = roll_no

        result_resp = session.post(MOBILE_RESULT_POST_URL, data=payload, headers=HEADERS, timeout=25)
        result_resp.raise_for_status()

        soup = BeautifulSoup(result_resp.text, "html.parser")
        title = _normalize_space(soup.title.get_text(" ", strip=True) if soup.title else "")
        exam_title = query_title or title

        # Safety gate: this feature is strictly for B.Tech 5th sem result page id.
        if exam_title and ("5th semester" not in exam_title.lower() or "b.tech" not in exam_title.lower()):
            return {
                "ok": False,
                "status": "wrong_exam_page",
                "message": "Only B.Tech 5th semester result is available right now.",
                "source": DESKTOP_QUERY_URL,
            }

        result_container = soup.find("div", class_="result_detail") or soup

        # Remove non-content tags to get cleaner visible text.
        for tag in result_container.find_all(["script", "style", "form", "noscript"]):
            tag.decompose()

        visible_text = _normalize_space(result_container.get_text(" ", strip=True))
        kv_data = _extract_key_values(result_container)
        subject_rows = _extract_subject_rows(result_container)
        text_kv_data = _extract_key_values_from_text(visible_text)

        # Merge table-derived and text-derived values (table values take precedence).
        merged_kv = dict(text_kv_data)
        merged_kv.update(kv_data)

        # Best-effort extraction from free text as fallback.
        text_roll_match = re.search(r"\b\d{5,15}\b", visible_text)
        candidate_roll = text_roll_match.group(0) if text_roll_match else ""

        # Heuristic for "not found": no useful extracted data.
        has_useful_rows = len(subject_rows) >= 2 or len(merged_kv) >= 2
        if not has_useful_rows:
            return {
                "ok": False,
                "status": "not_found",
                "message": "Result not found for this roll number in B.Tech 5th semester list.",
                "source": DESKTOP_QUERY_URL,
                "exam": exam_title,
            }

        # Pull common fields if present.
        def pick(*keys: str) -> str:
            for k in keys:
                if k in merged_kv:
                    return merged_kv[k]
            return ""

        name = pick("name", "candidate name", "student name", "name of candidate")
        final_result = pick("result", "final result", "status")
        sgpa = pick("sgpa")
        cgpa = pick("cgpa")

        return {
            "ok": True,
            "status": "found",
            "exam": exam_title,
            "roll_no": candidate_roll or roll_no,
            "name": name,
            "final_result": final_result,
            "sgpa": sgpa,
            "cgpa": cgpa,
            "rows": subject_rows[:20],
            "source": DESKTOP_QUERY_URL,
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status": "network_error",
            "message": f"Could not fetch result portal right now: {e}",
            "source": DESKTOP_QUERY_URL,
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "parse_error",
            "message": f"Could not parse result right now: {e}",
            "source": DESKTOP_QUERY_URL,
        }


def handle_btech_5th_result_query(user_message: str) -> str:
    """Build a chat-ready response for B.Tech 5th sem result queries."""
    roll_match = re.search(r"\b\d{5,15}\b", user_message or "")

    if not roll_match:
        name = _extract_name_from_message(user_message)
        if name:
            by_name = fetch_btech_5th_results_by_name(name)
            if by_name.get("ok"):
                lines = [
                    "Only B.Tech 5th sem result is available right now.",
                    "",
                    f"Name Search: {by_name.get('search_name', name)}",
                    f"Exam: {by_name.get('exam', 'B.Tech 5th Semester')}",
                    "",
                    "Matching candidates (use roll number to get full final result):",
                ]
                for item in (by_name.get("matches") or [])[:10]:
                    roll = item.get("roll_no", "")
                    cname = item.get("name", "")
                    if cname:
                        lines.append(f"- {cname} | Roll No: {roll}")
                    else:
                        lines.append(f"- Roll No: {roll}")
                lines.append("")
                lines.append("Tip: Send only the roll number to fetch detailed final result.")
                lines.append(f"Source: {by_name.get('source', DESKTOP_QUERY_URL)}")
                return "\n".join(lines)

            return (
                "Only B.Tech 5th sem result is available right now.\n\n"
                f"Name Search: {name}\n"
                f"Status: {by_name.get('message', 'No matching records found.')}\n"
                f"Check manually: {by_name.get('source', DESKTOP_QUERY_URL)}"
            )

        return (
            "Only B.Tech 5th sem result is available right now.\n\n"
            "Please enter your roll number OR full name to check result.\n"
            f"Result portal: {DESKTOP_QUERY_URL}"
        )

    roll_no = roll_match.group(0)
    data = fetch_btech_5th_result(roll_no)

    if not data.get("ok"):
        return (
            "Only B.Tech 5th sem result is available right now.\n\n"
            f"Roll No: {roll_no}\n"
            f"Status: {data.get('message', 'Result not available right now.')}\n"
            f"Check manually: {data.get('source', DESKTOP_QUERY_URL)}"
        )

    lines = [
        "Only B.Tech 5th sem result is available right now.",
        "",
        f"Exam: {data.get('exam', 'B.Tech 5th Semester')}",
        f"Roll No: {data.get('roll_no', roll_no)}",
    ]
    if data.get("name"):
        lines.append(f"Name: {data['name']}")
    if data.get("final_result"):
        lines.append(f"Final Result: {data['final_result']}")
    if data.get("sgpa"):
        lines.append(f"SGPA: {data['sgpa']}")
    if data.get("cgpa"):
        lines.append(f"CGPA: {data['cgpa']}")

    rows = data.get("rows") or []
    if rows:
        lines.append("")
        lines.append("Subject/Marks Details:")
        lines.extend([f"- {r}" for r in rows[:10]])

    lines.append("")
    lines.append(f"Source: {data.get('source', DESKTOP_QUERY_URL)}")
    return "\n".join(lines)
