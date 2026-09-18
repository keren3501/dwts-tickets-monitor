#!/usr/bin/env python3
"""
Checks on-camera-audiences.com's Dancing with the Stars page for specific
taping dates, and sends an ntfy.sh push notification if the button for one
of them changes away from "SUBMIT INFO" (meaning tickets/registration opened).

Matching is done purely by visible TEXT on the rendered page (not CSS
selectors or element ids), since the site injects the date cards via JS and
selectors are more likely to break silently than visible text is.

Run with --debug to print every date card it detected, so you can sanity
check the parsing against what the live page actually shows.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://on-camera-audiences.com/shows/dancing-with-the-stars/"
STATE_FILE = Path(__file__).parent / "state.json"

# Which dates to watch for. Add/remove entries here as needed.
TARGET_DATES = [
    {"label": "22/9/2026", "day": 22, "month_keywords": ["ספטמבר", "SEP", "September"]},
    {"label": "13/10/2026", "day": 13, "month_keywords": ["אוקטובר", "OCT", "October"]},
]

WEEKDAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M$", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")  # required to actually notify
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else None


def fetch_lines() -> list[str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)  # let any late JS rendering settle
        text = page.inner_text("body")
        browser.close()
    return [line.strip() for line in text.split("\n") if line.strip()]


def find_month_headers(lines: list[str]) -> list[tuple[int, str]]:
    """Lines that look like a month/year section header, e.g. '2026 אוקטובר'."""
    headers = []
    for i, line in enumerate(lines):
        if YEAR_RE.search(line) and len(line) < 40:
            headers.append((i, line))
    return headers


def nearest_header_before(headers: list[tuple[int, str]], idx: int) -> str:
    best = ""
    for h_idx, h_text in headers:
        if h_idx <= idx:
            best = h_text
        else:
            break
    return best


def find_cards(lines: list[str]) -> list[dict]:
    """
    Walks the linearized page text looking for the repeating pattern:
        <day number>
        <weekday, e.g. TUE>
        <status line, e.g. "TICKETS COMING SOON!">
        <time, e.g. "3:00 PM">
        <button text, e.g. "SUBMIT INFO">
    """
    headers = find_month_headers(lines)
    cards = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].isdigit() and 1 <= len(lines[i]) <= 2 and lines[i + 1].upper() in WEEKDAYS:
            day = int(lines[i])
            weekday = lines[i + 1].upper()
            # scan forward a few lines for a time + button pair
            window = lines[i + 2 : i + 6]
            time_idx = next((j for j, l in enumerate(window) if TIME_RE.match(l)), None)
            if time_idx is not None and time_idx + 1 < len(window):
                button = window[time_idx + 1]
                status = " ".join(window[:time_idx]) if time_idx > 0 else ""
                cards.append(
                    {
                        "day": day,
                        "weekday": weekday,
                        "month_header": nearest_header_before(headers, i),
                        "status": status,
                        "button": button,
                    }
                )
        i += 1
    return cards


def match_target(card: dict, target: dict) -> bool:
    if card["day"] != target["day"]:
        return False
    header = card["month_header"]
    return any(kw.lower() in header.lower() for kw in target["month_keywords"])


def send_ntfy(title: str, message: str):
    if not NTFY_URL:
        print(f"[ntfy skipped - no NTFY_TOPIC set] {title}: {message}")
        return
    req = urllib.request.Request(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": "high", "Tags": "tada"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        print(f"[ntfy sent] {title}: {message}")
    except Exception as e:
        print(f"[ntfy FAILED] {e}")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def main():
    debug = "--debug" in sys.argv
    lines = fetch_lines()
    cards = find_cards(lines)

    if debug:
        print(f"--- detected {len(cards)} card(s) ---")
        for c in cards:
            print(c)
        print("--- raw lines (for troubleshooting if 0 cards found) ---")
        print("\n".join(lines))
        return

    state = load_state()
    any_found = False

    for target in TARGET_DATES:
        matches = [c for c in cards if match_target(c, target)]
        if not matches:
            print(f"{target['label']}: not currently listed on the page")
            continue

        any_found = True
        card = matches[0]
        button_text = card["button"].strip()
        prev = state.get(target["label"])

        print(f"{target['label']}: button = '{button_text}' (previously: {prev!r})")

        is_open = button_text.upper() != "SUBMIT INFO"
        changed = prev != button_text

        if is_open and changed:
            send_ntfy(
                title=f"🎟️ DWTS tickets - {target['label']}",
                message=f"Button changed to: \"{button_text}\"\n{URL}",
            )

        state[target["label"]] = button_text

    if not any_found and cards:
        print(
            "Note: page has date cards, but none matched the target dates - "
            "they may not be listed yet (site shows up to 60 days ahead), "
            "or parsing needs adjusting. Run with --debug to inspect."
        )
    elif not cards:
        print(
            "Note: 0 date cards detected at all - parsing may need adjusting "
            "for a site layout change. Run with --debug to inspect."
        )

    save_state(state)


if __name__ == "__main__":
    main()
