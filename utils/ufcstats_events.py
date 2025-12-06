import requests
from bs4 import BeautifulSoup

UFC_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"


def get_next_ufc_event():
    """
    Scrapes UFCStats upcoming events and returns:
    - event_name
    - event_date
    - location
    - event_url
    - fight_card (list)
    """

    # --------------------------------------------------
    # Fetch upcoming events page
    # --------------------------------------------------
    html = requests.get(UFC_UPCOMING, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("tbody tr")

    if not rows:
        return {"error": "No events found on UFCStats."}

    next_event = None

    # --------------------------------------------------
    # Find first real event row
    # --------------------------------------------------
    for r in rows:
        cols = r.find_all("td")

        # must have 3 columns
        if len(cols) < 3:
            continue

        # must have an <a> link in first column
        link = cols[0].find("a")
        if not link:
            continue

        event_url = link.get("href")
        event_name = link.get_text(strip=True)

        # valid event rows always have date/location
        event_date = cols[1].get_text(strip=True)
        location   = cols[2].get_text(strip=True)

        # once we reach here, we found the next real event
        next_event = {
            "event_name": event_name,
            "event_date": event_date,
            "location": location,
            "event_url": event_url
        }
        break

    if not next_event:
        return {"error": "Could not locate valid upcoming event."}

    # --------------------------------------------------
    # Fetch event page (fight card)
    # --------------------------------------------------
    event_html = requests.get(next_event["event_url"], timeout=10).text
    es = BeautifulSoup(event_html, "html.parser")

    fight_rows = es.select(".b-fight-details__table-body tr")

    fight_card = []

    for fr in fight_rows:
        cells = fr.find_all("td")
        if len(cells) < 3:
            continue

        fighter_a = cells[1].get_text(strip=True)
        fighter_b = cells[2].get_text(strip=True)

        if fighter_a and fighter_b:
            fight_card.append({
                "fighter_a": fighter_a,
                "fighter_b": fighter_b
            })

    next_event["fight_card"] = fight_card
    return next_event
