import requests
from bs4 import BeautifulSoup
from utils.openai_client import client
import time

UFC_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"


def scrape_next_event():
    """
    Attempts to scrape UFCStats upcoming events.
    Returns event dict OR None if it fails.
    """

    try:
        html = requests.get(UFC_UPCOMING, timeout=12).text
    except:
        return None  # let caller fall back to GPT

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
        location = cols[2].get_text(strip=True)

        next_event = {
            "event_name": event_name,
            "event_date": event_date,
            "location": location,
            "event_url": event_url
        }
        break

    if not next_event:
        return None

    # Now scrape the event page for fight card
    try:
        event_html = requests.get(next_event["event_url"], timeout=12).text
    except:
        return None

    es = BeautifulSoup(event_html, "html.parser")

    fights = []
    fight_rows = es.select(".b-fight-details__table-body tr")

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
    If UFCStats scraping fails, use GPT (search-only, no browsing)
    to retrieve next UFC event safely.
    """

    prompt = """
Find the NEXT upcoming UFC event.
Do NOT browse websites.
Use your internal knowledge + search.

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

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(res.choices[0].message.content)
    except:
        return {"error": "GPT fallback failed."}


def get_next_ufc_event():
    """
    Master function:
    1. Try scraping UFCStats up to 3 times.
    2. If all retry attempts fail → fallback to GPT.
    """

    # Try scraping 3 times
    for attempt in range(3):
        ev = scrape_next_event()
        if ev:
            return ev

        # backoff
        time.sleep(1 + attempt)

    # Scraping failed — now use GPT fallback
    return gpt_fallback_next_event()
