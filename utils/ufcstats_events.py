import requests
from bs4 import BeautifulSoup

UFC_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"

def get_next_ufc_event():
    """
    Scrapes UFCStats upcoming events page and returns
    the next event with:
    - event_name
    - event_date
    - location
    - event_url
    - fight_card_url
    - fight_card (list of dicts)
    """

    html = requests.get(UFC_UPCOMING, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("tbody tr")

    if not rows:
        return {"error": "No events found"}

    # First row = next UFC event
    first = rows[0]
    cols = first.find_all("td")

    event_url = cols[0].find("a")["href"]
    event_name = cols[0].get_text(strip=True)
    event_date = cols[1].get_text(strip=True)
    location   = cols[2].get_text(strip=True)

    # Now scrape event page for fight card
    event_page = requests.get(event_url, timeout=10).text
    event_soup = BeautifulSoup(event_page, "html.parser")

    fights = []

    fight_rows = event_soup.select(".b-fight-details__table-body tr")

    for fr in fight_rows:
        cells = fr.find_all("td")
        if len(cells) < 2:
            continue

        fighter_a = cells[1].get_text(strip=True)
        fighter_b = cells[2].get_text(strip=True)

        if fighter_a and fighter_b:
            fights.append({
                "fighter_a": fighter_a,
                "fighter_b": fighter_b
            })

    return {
        "event_name": event_name,
        "event_date": event_date,
        "location": location,
        "event_url": event_url,
        "fight_card": fights
    }
