"""
Result Service — B.Tech 5th semester result lookup from IndiaResults.
Handles roll number submission and lightweight parsing of the result page.
"""
import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


DESKTOP_QUERY_URL = "https://himturesult.indiaresults.com/hp/himtu/hp-himtu/query.aspx?id=1800266751"
MOBILE_QUERY_URL = "https://results.indiaresults.com/hp/himtu/hp-himtu/mquery.aspx?id=1800266751"
MOBILE_RESULT_POST_URL = "https://results.indiaresults.com/hp/himtu/mresult.aspx"
RESULTS_HOME_URL = "https://himturesult.indiaresults.com/hp/himtu/default.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": DESKTOP_QUERY_URL,
}

# Lightweight in-memory cache for latest query links.
_query_cache = {
    "items": [],
    "fetched_at": 0.0,
}


def _extract_query_id(query_url: str) -> str:
    m = re.search(r"[?&]id=(\d+)", query_url or "")
    return m.group(1) if m else ""


def _is_generic_result_page(text: str) -> bool:
    low = (text or "").lower()
    return "select state" in low and "indiaresults" in low


def _get_recent_query_links(max_items: int = 80) -> List[Dict[str, str]]:
    """Load latest result query links from IndiaResults home, with cache."""
    now = time.time()
    if _query_cache["items"] and now - _query_cache["fetched_at"] < 900:
        return _query_cache["items"][:max_items]

    items: List[Dict[str, str]] = []
    try:
        resp = requests.get(RESULTS_HOME_URL, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "query.aspx?id=" not in href:
                continue
            url = requests.compat.urljoin(RESULTS_HOME_URL, href)
            qid = _extract_query_id(url)
            if not qid or qid in seen:
                continue
            seen.add(qid)
            title = _normalize_space(a.get_text(" ", strip=True))
            items.append({"query_url": url, "title": title, "id": qid})
            if len(items) >= max_items:
                break
    except Exception as e:
        print(f"Result query-link scrape error: {e}")

    # Always keep configured query first.
    configured = {
        "query_url": DESKTOP_QUERY_URL,
        "title": "Configured default result page",
        "id": _extract_query_id(DESKTOP_QUERY_URL),
    }
    merged: List[Dict[str, str]] = [configured]
    merged.extend([i for i in items if i.get("id") != configured["id"]])

    _query_cache["items"] = merged
    _query_cache["fetched_at"] = now
    return merged[:max_items]


def _fetch_query_context(session: requests.Session, query_url: str) -> Dict[str, str]:
    """Fetch query page and return title plus JS-equivalent roll/name action URLs."""
    query_resp = session.get(query_url, headers={**HEADERS, "Referer": query_url}, timeout=25)
    query_resp.raise_for_status()
    query_soup = BeautifulSoup(query_resp.text, "html.parser")
    query_title = _normalize_space(query_soup.title.get_text(" ", strip=True) if query_soup.title else "")

    suffix = "?chk=Y" if "chk=Y" in query_url else ""
    # Query page JS sets these on button click:
    # show_roll_result -> result.aspx
    # show_name_result -> name-results.aspx
    roll_action_url = requests.compat.urljoin(query_url, f"result.aspx{suffix}")
    name_action_url = requests.compat.urljoin(query_url, f"name-results.aspx{suffix}")
    payload = _extract_hidden_fields(query_resp.text)

    return {
        "title": query_title,
        "roll_action_url": roll_action_url,
        "name_action_url": name_action_url,
        "payload": payload,
        "query_url": query_url,
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
        "name": [
            r"(?:candidate\s*name|student\s*name|name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{1,60}?)(?=\s+father|\s+marks|\s+result|$)",
        ],
        "roll no": [r"(?:roll\s*no\.?|roll\s*number)\s*[:\-]?\s*(\d{5,15})"],
        "result": [
            r"(?:final\s*result|result|status)\s*[:\-]?\s*(PASS|FAIL|RE-APPEAR|REAPPEAR|PASSED|FAILED)",
        ],
        "sgpa": [r"sgpa\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
        "cgpa": [r"cgpa\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
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
    """Extract subject-wise rows in clean 'Subject | Code | Credit | Grade' format."""
    # Prefer table-structured extraction from the marks-details table.
    for table in result_container.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        header_cells = [
            _normalize_space(c.get_text(" ", strip=True)).lower()
            for c in rows[0].find_all(["td", "th"])
        ]
        has_marks_headers = (
            "subject" in header_cells
            and "subject code" in header_cells
            and "credit" in header_cells
            and "grade" in header_cells
        )
        if not has_marks_headers:
            continue

        subject_lines: List[str] = []
        for tr in rows[1:]:
            cells = [
                _normalize_space(c.get_text(" ", strip=True))
                for c in tr.find_all(["td", "th"])
            ]
            cells = [c for c in cells if c]
            if len(cells) < 4:
                continue

            subject = cells[0]
            code = cells[1]
            credit = cells[2]
            grade = cells[3]

            # Ignore footer/non-subject rows.
            if subject.lower() in {"final result", "remarks"}:
                continue
            if len(subject) < 2 or not re.search(r"[A-Za-z]", subject):
                continue

            subject_lines.append(f"{subject} | {code} | Credit: {credit} | Grade: {grade}")

        if subject_lines:
            return subject_lines

    # Fallback: extract common subject-code rows directly from plain text.
    text = _normalize_space(result_container.get_text(" ", strip=True))
    matches = re.findall(
        r"([A-Za-z][A-Za-z0-9&()'\-\s]{2,80}?)\s+(CSPC-\d{3}P?)\s+(\d+)\s+([A-F][+]?)\b",
        text,
        flags=re.IGNORECASE,
    )

    lines: List[str] = []
    seen_codes = set()
    for subject, code, credit, grade in matches:
        code_u = code.upper()
        if code_u in seen_codes:
            continue
        seen_codes.add(code_u)
        clean_subject = _normalize_space(subject)
        # Remove accidental leading labels when text is flattened.
        clean_subject = re.sub(r"^(?:subject|marks\s+details)\s+", "", clean_subject, flags=re.IGNORECASE)
        for marker in ["marks details", "subject subject code credit grade", "grade", "student name", "father's name"]:
            idx = clean_subject.lower().rfind(marker)
            if idx >= 0:
                clean_subject = _normalize_space(clean_subject[idx + len(marker):])
        if not clean_subject:
            clean_subject = "Subject"
        lines.append(f"{clean_subject} | {code_u} | Credit: {credit} | Grade: {grade.upper()}")

    return lines


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

    return _fetch_name_results_from_query(name, DESKTOP_QUERY_URL, enforce_btech_5th=True)


def _fetch_name_results_from_query(name: str, query_url: str, enforce_btech_5th: bool = False) -> Dict[str, object]:
    """Search by name within a specific query URL."""
    try:
        session = requests.Session()
        query_ctx = _fetch_query_context(session, query_url)
        query_title = query_ctx.get("title", "")
        if enforce_btech_5th and query_title and ("5th semester" not in query_title.lower() or "b.tech" not in query_title.lower()):
            return {
                "ok": False,
                "status": "wrong_exam_page",
                "message": "Only B.Tech 5th semester result is available right now.",
                "source": query_url,
            }

        payload = query_ctx.get("payload", {})
        payload["txtName"] = name

        headers = {**HEADERS, "Referer": query_url}
        resp = session.post(query_ctx.get("name_action_url", query_url), data=payload, headers=headers, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        visible_text = _normalize_space(soup.get_text(" ", strip=True))

        candidates = _extract_name_candidates(soup)
        if not candidates:
            status = "not_found_name"
            message = f"No result found for name '{name}' in this list."
            if _is_generic_result_page(visible_text):
                status = "query_no_match_name"
                message = f"No matching name found in this result list for '{name}'."
            return {
                "ok": False,
                "status": status,
                "message": message,
                "exam": query_title,
                "source": query_url,
            }

        return {
            "ok": True,
            "status": "found_name",
            "exam": query_title,
            "search_name": name,
            "matches": candidates[:15],
            "source": query_url,
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status": "network_error",
            "message": f"Could not fetch result portal right now: {e}",
            "source": query_url,
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "parse_error",
            "message": f"Could not parse name search result right now: {e}",
            "source": query_url,
        }


def fetch_result_by_name_any_exam(name: str, max_queries: int = 30) -> Dict[str, object]:
    """Try multiple recent HIMTU result query IDs and return matching names/roll numbers."""
    queries = _get_recent_query_links(max_items=max_queries)
    if not queries:
        return {
            "ok": False,
            "status": "no_query_links",
            "message": "Could not load result lists right now.",
            "source": RESULTS_HOME_URL,
        }

    collected: List[Dict[str, str]] = []
    seen_rolls = set()
    last_error = None

    for item in queries:
        query_url = item.get("query_url", "")
        data = _fetch_name_results_from_query(name, query_url, enforce_btech_5th=False)
        if data.get("ok"):
            exam = data.get("exam", "")
            for match in data.get("matches", []):
                roll = match.get("roll_no", "")
                if not roll or roll in seen_rolls:
                    continue
                seen_rolls.add(roll)
                collected.append({
                    "roll_no": roll,
                    "name": match.get("name", ""),
                    "exam": exam,
                })
                if len(collected) >= 20:
                    break
        elif data.get("status") in {"network_error", "parse_error"}:
            last_error = data

        if len(collected) >= 20:
            break

    if collected:
        return {
            "ok": True,
            "status": "found_name_any",
            "search_name": name,
            "matches": collected,
            "source": RESULTS_HOME_URL,
        }

    if last_error:
        return last_error

    return {
        "ok": False,
        "status": "not_found_name_any",
        "message": f"No matching result found in recent HIMTU result lists for name '{name}'.",
        "source": RESULTS_HOME_URL,
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

    return _fetch_roll_result_from_query(roll_no, DESKTOP_QUERY_URL, enforce_btech_5th=True)


def _fetch_roll_result_from_query(roll_no: str, query_url: str, enforce_btech_5th: bool = False) -> Dict[str, object]:
    """Fetch roll result from a specific IndiaResults query URL."""
    try:
        session = requests.Session()
        query_ctx = _fetch_query_context(session, query_url)
        query_title = query_ctx.get("title", "")

        # Safety gate when caller wants strict B.Tech 5th semantics.
        if enforce_btech_5th and query_title and ("5th semester" not in query_title.lower() or "b.tech" not in query_title.lower()):
            return {
                "ok": False,
                "status": "wrong_exam_page",
                "message": "Only B.Tech 5th semester result is available right now.",
                "source": query_url,
            }

        payload = query_ctx.get("payload", {})
        payload["RollNo"] = roll_no

        headers = {**HEADERS, "Referer": query_url}
        result_resp = session.post(query_ctx.get("roll_action_url", MOBILE_RESULT_POST_URL), data=payload, headers=headers, timeout=25)
        result_resp.raise_for_status()

        soup = BeautifulSoup(result_resp.text, "html.parser")
        title = _normalize_space(soup.title.get_text(" ", strip=True) if soup.title else "")
        exam_title = query_title or title

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

        has_useful_rows = len(subject_rows) >= 2 or len(merged_kv) >= 2
        if not has_useful_rows:
            status = "not_found"
            message = "Result not found for this roll number in this result list."
            if _is_generic_result_page(visible_text):
                status = "query_no_match"
                message = "No matching record found in this result list."
            return {
                "ok": False,
                "status": status,
                "message": message,
                "source": query_url,
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
            "source": query_url,
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status": "network_error",
            "message": f"Could not fetch result portal right now: {e}",
            "source": query_url,
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "parse_error",
            "message": f"Could not parse result right now: {e}",
            "source": query_url,
        }


def fetch_result_any_exam(roll_no: str, max_queries: int = 30) -> Dict[str, object]:
    """Try multiple recent HIMTU result query IDs and return first matching roll result."""
    queries = _get_recent_query_links(max_items=max_queries)
    if not queries:
        return {
            "ok": False,
            "status": "no_query_links",
            "message": "Could not load result lists right now.",
            "source": RESULTS_HOME_URL,
        }

    last_error = None
    for item in queries:
        query_url = item.get("query_url", "")
        data = _fetch_roll_result_from_query(roll_no, query_url, enforce_btech_5th=False)
        if data.get("ok"):
            return data

        if data.get("status") in {"network_error", "parse_error"}:
            last_error = data

    if last_error:
        return last_error

    return {
        "ok": False,
        "status": "not_found_any",
        "message": "No matching result found in recent HIMTU result lists.",
        "source": RESULTS_HOME_URL,
    }


def handle_btech_5th_result_query(user_message: str) -> str:
    """Build a chat-ready response for HIMTU result queries in chat."""
    roll_match = re.search(r"\b\d{5,15}\b", user_message or "")

    if not roll_match:
        name = _extract_name_from_message(user_message)
        if name:
            by_name = fetch_btech_5th_results_by_name(name)
            if not by_name.get("ok") and by_name.get("status") in {"not_found_name", "query_no_match_name"}:
                by_name = fetch_result_by_name_any_exam(name, max_queries=25)

            if by_name.get("ok"):
                lines = [
                    "Result found.",
                    "",
                    f"Name Search: {by_name.get('search_name', name)}",
                    "Matching candidates (use roll number to get full final result):",
                ]
                for item in (by_name.get("matches") or [])[:10]:
                    roll = item.get("roll_no", "")
                    cname = item.get("name", "")
                    exam = item.get("exam", by_name.get("exam", ""))
                    if cname:
                        line = f"- {cname} | Roll No: {roll}"
                    else:
                        line = f"- Roll No: {roll}"
                    if exam:
                        line += f" | {exam}"
                    lines.append(line)
                lines.append("")
                lines.append("Tip: Send only the roll number to fetch detailed final result.")
                lines.append(f"Source: {by_name.get('source', RESULTS_HOME_URL)}")
                return "\n".join(lines)

            return (
                "No matching result found.\n\n"
                f"Name Search: {name}\n"
                f"Status: {by_name.get('message', 'No matching records found in recent result lists.')}\n"
                f"Check manually: {by_name.get('source', RESULTS_HOME_URL)}"
            )

        return (
            "To check result, enter your roll number OR full name.\n\n"
            "Please enter your roll number OR full name to check result.\n"
            f"Result portal: {RESULTS_HOME_URL}"
        )

    roll_no = roll_match.group(0)
    data = fetch_btech_5th_result(roll_no)
    if not data.get("ok") and data.get("status") in {"not_found", "query_no_match"}:
        data = fetch_result_any_exam(roll_no, max_queries=25)

    if not data.get("ok"):
        return (
            "No matching result found.\n\n"
            f"Roll No: {roll_no}\n"
            f"Status: {data.get('message', 'Result not available right now.')}\n"
            f"Check manually: {data.get('source', RESULTS_HOME_URL)}"
        )

    lines = [
        "Result found.",
        "",
        f"Exam: {data.get('exam', 'HIMTU Result')}",
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
