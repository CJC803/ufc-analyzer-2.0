import streamlit as st
import json
import pandas as pd
import time
import math

from utils.openai_client import client
from utils.batch_fighter_lookup import batch_fighter_lookup
from utils.batch_odds_lookup import batch_odds_lookup
from utils.batch_tapology import batch_tapology_histories
from utils.sherdog_scraper import fetch_sherdog_profile
from utils.ufcstats_scraper import fetch_ufcstats
from utils.fighter_merger import merge_fighter_profile
from utils.usage_limit import usage_ok
from utils.helpers import safe_json_load

# -----------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------
st.set_page_config(
    page_title="UFC Fight Card Analyzer (Elite Mode)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🥋 UFC Fight Card Analyzer – **Elite Mode**")


# -----------------------------------------------------
# LOAD PROMPTS
# -----------------------------------------------------
def load_prompt(path):
    with open(path, "r") as f:
        return f.read()

system_prompt     = load_prompt("prompts/system_prompt.txt")
event_prompt      = load_prompt("prompts/event_lookup_prompt.txt")
analysis_prompt   = load_prompt("prompts/analysis_prompt.txt")


# -----------------------------------------------------
# GPT WRAPPER
# -----------------------------------------------------
@st.cache_data(show_spinner=False)
def call_gpt_cached(prompt):
    """Cached GPT call"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


def call_gpt_uncached(prompt):
    """Non-cached GPT call (use sparingly)"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


# -----------------------------------------------------
# GET NEXT UFC EVENT
# -----------------------------------------------------
def get_next_event():
    raw = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": event_prompt}],
        temperature=0
    )
    return safe_json_load(raw.choices[0].message.content)


# -----------------------------------------------------
# TAPOLOGY BATCH BREAKER (8 fighters per batch)
# -----------------------------------------------------
def run_tapology_batches(fighter_list):
    BATCH = 8
    tapology_full = {}

    # Break into chunks
    for i in range(0, len(fighter_list), BATCH):
        chunk = fighter_list[i:i+BATCH]
        with st.spinner(f"Fetching Tapology histories for: {', '.join(chunk)}"):
            result = batch_tapology_histories(chunk)
            tapology_full.update(result.get("fighters", {}))
            time.sleep(0.4)  # rate limit friendly

    return tapology_full


# -----------------------------------------------------
# FIGHTER DATA PIPELINE
# -----------------------------------------------------
def process_fighters(event_data):
    """Main fighter-processing pipeline using batch GPT calls."""

    # Extract names
    fighter_names = []
    for fight in event_data["fight_card"]:
        fighter_names.append(fight["fighter_a"])
        fighter_names.append(fight["fighter_b"])

    fighter_names = list(dict.fromkeys(fighter_names))  # dedupe

    # --------------------
    # 1) Batch metadata lookup
    # --------------------
    with st.spinner("🔍 Gathering fighter metadata..."):
        meta = batch_fighter_lookup(fighter_names)
        fighter_meta = meta["fighters"]

    # --------------------
    # 2) Batch Tapology histories
    # --------------------
    tapology_histories = run_tapology_batches(fighter_names)

    # --------------------
    # 3) Sherdog + UFCStats scraping
    # --------------------
    sherdog_data = {}
    ufcstats_data = {}

    for name in fighter_names:
        meta_info = fighter_meta[name]

        # Sherdog scrape
        url = meta_info.get("sherdog_url", "")
        if url:
            with st.spinner(f"Scraping Sherdog for {name}..."):
                sherdog_data[name] = fetch_sherdog_profile(url)
        else:
            sherdog_data[name] = []

        # UFCStats scrape
        fid = meta_info.get("ufcstats_id", "")
        if fid:
            with st.spinner(f"Scraping UFCStats for {name}..."):
                ufcstats_data[name] = fetch_ufcstats(fid)
        else:
            ufcstats_data[name] = {}

    # --------------------
    # 4) Batch odds lookup for all fights
    # --------------------
    fight_labels = [
        f"{fight['fighter_a']} vs {fight['fighter_b']}"
        for fight in event_data["fight_card"]
    ]

    with st.spinner("💰 Retrieving odds for full card..."):
        odds_full = batch_odds_lookup(fight_labels)["odds"]

    return wrestler_merge(meta=fighter_meta,
                          tap=tapology_histories,
                          sd=sherdog_data,
                          uf=ufcstats_data,
                          odds=odds_full,
                          event_data=event_data)


# -----------------------------------------------------
# MERGE EVERYTHING
# -----------------------------------------------------
def wrestler_merge(meta, tap, sd, uf, odds, event_data):
    """Merge into final structure used for analysis."""
    merged = {}

    for fight in event_data["fight_card"]:
        A = fight["fighter_a"]
        B = fight["fighter_b"]

        label = f"{A} vs {B}"
        fight_odds = odds.get(label, {})

        merged[label] = {
            A: merge_fighter_profile(
                A,
                meta.get(A, {}),
                tap.get(A, []),
                sd.get(A, []),
                uf.get(A, {}),
                fight_odds
            ),
            B: merge_fighter_profile(
                B,
                meta.get(B, {}),
                tap.get(B, []),
                sd.get(B, []),
                uf.get(B, {}),
                fight_odds
            ),
            "odds": fight_odds
        }

    return merged


# -----------------------------------------------------
# RUN FINAL FIGHT-CARD ANALYSIS
# -----------------------------------------------------
def run_final_analysis(merged, event_data):
    payload = {
        "event": event_data,
        "merged_fighters": merged
    }

    prompt = f"""
Use this structured dataset to produce elite-level UFC fight analysis.

Data:
{json.dumps(payload, indent=2)}

Instructions:
{analysis_prompt}
"""

    with st.spinner("🧠 Running full analysis..."):
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return result.choices[0].message.content


# -----------------------------------------------------
# UI TABS
# -----------------------------------------------------
tab1, tab2 = st.tabs(["🔥 Analyze Next UFC Event", "📅 Analyze Custom Event"])

# =====================================================
# TAB 1 — AUTO-MODE
# =====================================================
with tab1:
    st.header("🔥 Auto Mode — Next UFC Event")

    if st.button("Analyze Next UFC Event"):
        if not usage_ok():
            st.error("Daily usage limit reached. Try again tomorrow.")
            st.stop()

        # 1) Get next event
        with st.spinner("📅 Locating next UFC event..."):
            event_data = get_next_event()

        st.subheader(event_data["event_name"])
        st.write(f"**Date:** {event_data['event_date']}")
        st.write(f"**Location:** {event_data['location']}")
        st.divider()

        # 2) Fighter processing pipeline
        merged = process_fighters(event_data)

        # 3) Final analysis
        analysis = run_final_analysis(merged, event_data)

        st.markdown("## 📘 Full Card Analysis")
        st.markdown(analysis)


# =====================================================
# TAB 2 — CUSTOM EVENT URL
# =====================================================
with tab2:
    st.header("📅 Analyze Any UFC Event URL")

    event_url = st.text_input("Paste a UFC/Tapology event URL:")

    if st.button("Analyze This Event"):
        if not usage_ok():
            st.error("Daily usage limit reached.")
            st.stop()

        # Let GPT interpret custom URL
        custom_prompt = f"""
Parse this fight card URL and extract:

- event_name
- event_date
- location
- fight_card

Return strict JSON.

URL:
{event_url}
"""
        with st.spinner("🔍 Reading event data..."):
            raw = call_gpt_uncached(custom_prompt)
            event_data = safe_json_load(raw)

        st.subheader(event_data["event_name"])

        merged = process_fighters(event_data)
        analysis = run_final_analysis(merged, event_data)

        st.markdown(analysis)
