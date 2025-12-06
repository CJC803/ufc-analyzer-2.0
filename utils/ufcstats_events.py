import requests
from bs4 import BeautifulSoup
import json
import time

from utils.openai_client import client
from utils.gpt_safe import gpt_safe_call


UFC_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"


def scrape_next_event():
    """Attempts to scrape UFCStats for upcoming events. Returns event dict OR None."""

    try:
        html = requests.get(UFC_UPCOMING, timeout=12).text
    except:
        return None

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tbody tr")

    if not rows:
        return None

    next_event = None

    for r in rows:
        cols = r.find_all("td")
        if len(cols) < 3:
            continue

        link = cols[0].find("a")
        if not link:
            continue

        event_url = link.get("href")
        event_name = link.get_text(strip=True)
        event_date = cols[1].get_text(strip=True)
        location   = cols[2].get_text(strip=True)

        next_event = {
            "event_name": event_name,
            "event_date": event_date,
            "location": location,
            "event_url": event_url
        }
        break

    if not next_event:
        return None

    # Scrape event card
    try:
        ehtml = requests.get(next_event["event_url"], timeout=12).text
    except:
        return None

    es = BeautifulSoup(ehtml, "html.parser")
    fight_rows = es.select(".b-fight-details__table-body tr")

    fights = []

    for fr in fight_rows:
        cells = fr.find_all("td")
        if len(cells) < 3:
            continue

        a = cells[1].get_text(strip=True)
        b = cells[2].get_text(strip=True)

        if a and b:
            fights.append({"fighter_a": a, "fighter_b": b})

    next_event["fight_card"] = fights
    return next_event


def gpt_fallback_next_event():
    """
    Uses GPT (search-only, no browsing) to retrieve the next UFC event.
    Now wrapped with gpt_safe_call to avoid rate limits.
    """

    prompt = """
Find the NEXT upcoming UFC event using search (NOT browsing).
Return STRICT JSON:

{
  "event_name": "",
  "event_date": "",
  "location": "",
  "fight_card": [
    {"fighter_a": "", "fighter_b": ""}
  ]
}
"""

    raw = gpt_safe_call([
        {"role": "user", "content": prompt}
    ])

    return json.loads(raw)


def get_next_ufc_event():
    """
    Master function:
    1. Try scraping UFCStats up to 3 times (with backoff).
    2. If scraping fails, fall back to GPT-safe event fetch.
    """

    for attempt in range(3):
        result = scrape_next_event()
        if result:
            return result
        time.sleep(1 + attempt)

    # fallback
    return gpt_fallback_next_event()
