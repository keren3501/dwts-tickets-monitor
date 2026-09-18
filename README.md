# DWTS ticket checker

Checks https://on-camera-audiences.com/shows/dancing-with-the-stars/ every
hour via GitHub Actions (a real headless Chromium, so it sees the
JS-rendered date cards), and pushes an ntfy.sh notification if the button
for **22/9/2026** or **13/10/2026** changes away from "SUBMIT INFO".

Matching is done by visible text (day number + weekday + nearby month
header), not by CSS selectors/ids, so it should keep working even if the
site's class names or ids change.

## Setup

1. Create a new (can be private) GitHub repo and add these files:
   - `check_tickets.py`
   - `requirements.txt`
   - `.github/workflows/check-tickets.yml` (the `check-tickets.yml` file
     here goes in that path, i.e. inside a `.github/workflows/` folder)

2. Get notifications on your phone with **ntfy.sh** (free, no signup):
   - Install the ntfy app ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/app/ntfy/id1625396347)), or just use the web at https://ntfy.sh
   - Pick a topic name only you know (topics are just secret-ish strings -
     anyone who knows the exact name can subscribe or publish to it). A
     suggestion: `keren-dwts-f2285a07`
   - In the app, "Subscribe to topic" with that exact name.

3. In your GitHub repo: **Settings → Secrets and variables → Actions →
   New repository secret**
   - Name: `NTFY_TOPIC`
   - Value: the topic name you picked above

4. Make sure Actions are enabled for the repo (Settings → Actions →
   General → Allow all actions), and that the default `GITHUB_TOKEN` has
   **Read and write permissions** (Settings → Actions → General →
   Workflow permissions) - needed so the workflow can commit `state.json`
   back to the repo between runs.

That's it - it'll start running hourly on its own schedule. You can also
trigger a run manually any time from the repo's **Actions** tab →
"Check DWTS ticket status" → **Run workflow**, which is the easiest way to
test it end-to-end once it's set up.

## Testing / debugging locally

```bash
pip install -r requirements.txt
playwright install chromium
python check_tickets.py --debug
```

This prints every date card it detected on the live page (so you can see
immediately if the parsing needs adjusting) without sending any
notification. Run it without `--debug` to do a real check (it'll print
"ntfy skipped" instead of actually notifying if `NTFY_TOPIC` isn't set in
your environment).

## Adjusting the watched dates

Edit the `TARGET_DATES` list near the top of `check_tickets.py` - add,
remove, or change dates there. Each entry needs the day-of-month number and
a couple of keywords (Hebrew/English) that appear in that month's section
header on the page.

## Notes

- If the site redesigns the date-cards section, `find_cards()` may need
  tweaking - run with `--debug` to see the raw detected lines and adjust
  the pattern-matching in `check_tickets.py`.
- The tool description on the site says tickets are usually released via
  email through their weekly lottery (typically Fridays), and dates are
  only posted up to 60 days ahead - so a date not appearing at all on the
  page yet is expected and not itself something to worry about.
