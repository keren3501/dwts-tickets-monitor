#!/usr/bin/env python3
"""
One-off diagnostic: figure out WHERE the "SHOW DATES" calendar actually
lives on the page - an iframe, or content revealed after clicking
"GET TICKETS". Run this once and share the full output.
"""

from playwright.sync_api import sync_playwright

URL = "https://on-camera-audiences.com/shows/dancing-with-the-stars/"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Log every network response that isn't a common static asset -
        # this often reveals the API call that actually returns the dates.
        print("=== NETWORK RESPONSES (non-asset) ===")

        def on_response(resp):
            url = resp.url
            if any(url.endswith(ext) for ext in (".js", ".css", ".png", ".jpg", ".svg", ".woff", ".woff2", ".ico")):
                return
            try:
                ctype = resp.headers.get("content-type", "")
            except Exception:
                ctype = "?"
            print(f"  [{resp.status}] {ctype} {url}")

        page.on("response", on_response)

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        print("\n=== FRAMES ON PAGE ===")
        for f in page.frames:
            print(f"\n--- frame: {f.url} ---")
            try:
                txt = f.inner_text("body")
                print(txt[:2000] if txt else "(empty)")
            except Exception as e:
                print(f"(could not read: {e})")

        print("\n=== TRYING TO CLICK 'GET TICKETS' ===")
        try:
            btn = page.get_by_text("GET TICKETS", exact=False).first
            btn.click(timeout=5000)
            page.wait_for_timeout(3000)
            print("Clicked. Body text after click:")
            print(page.inner_text("body")[:3000])
        except Exception as e:
            print(f"Could not click / no change: {e}")

        page.screenshot(path="after_click.png", full_page=True)
        print("\nSaved screenshot to after_click.png")

        browser.close()


if __name__ == "__main__":
    main()
