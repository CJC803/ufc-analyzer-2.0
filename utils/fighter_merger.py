def merge_fighter_profile(
    name,
    meta,
    tapology_history,
    sherdog_history,
    ufcstats,
    odds
):
    return {
        "name": name,
        "meta": meta,
        "tapology": tapology_history,
        "sherdog": sherdog_history,
        "ufcstats": ufcstats,
        "odds": odds
    }
