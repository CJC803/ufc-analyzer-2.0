import streamlit as st
import json
import time

from utils.openai_client import client
from utils.ufcstats_events import get_next_ufc_event
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
)

st.title("🥋 UFC Fight Card Analyzer — **Elite Mode**")


# -----------------------------------------------------
# LOAD PROMPTS
# -----------------------------------------------------
def load_prompt(path):
    with open(path, "r") as f:
        return f.read()

system_prompt   = load_prompt("prompts/system_prompt.txt")
analysis_prompt = load_prompt("prompts/analysis_prompt.txt")


# -----------------------------------------------------
# GPT HELPERS
# -----------------------------------------------------
def call_gpt(payload):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": payload}]
    )
    return res.choices[0].message.content


# -----------------------------------------------------
# TAPOLOGY BATCHER (8 fighters)
# -----------------------------------------------------
def run_tapology_batches(fighter_list):
    BATCH = 8
    tap = {}
    for i in range(0, len(fighter_list), BATCH):
        chunk = fighter_list[i:i+BATCH]
        with st.spinner(f"📄 Retrieving Tapology histories for: {', '.join(chunk)}"):
            result = batch_tapology_histories(chunk)
            tap.update(result.get("fighters", {}))
            time.sleep(0.4)
    return tap


# -----------------------------------------------------
# FIGHTER PROCESS PIPELINE
# -----------------------------------------------------
def process_fighters(event_data):
    fighter_names = []
    for fight in event_data["fight_card"]:
        fighter_names.append(fight["fighter_a"])
        fighter_names.append(fight["fighter_b"])

    fighter_names = list(dict.fromkeys(fighter_names))

    # metadata
    with st.spinner("🔎 Fetching fighter metadata..."):
        meta = batch_fighter_lookup(fighter_names)["fighters"]

    # tapology
    tap = run_tapology_batches(fighter_names)

    # scrapers
    sd = {}
    uf = {}

    for name in fighter_names:
        meta_info = meta.get(name, {})

        # Sherdog
        s_url = meta_info.get("sherdog_url", "")
        if s_url:
            with st.spinner(f"🐶 Sherdog for {name}"):
                sd[name] = fetch_sherdog_profile(s_url)
        else:
            sd[name] = []

        # UFCStats
        fid = meta_info.get("ufcstats_id", "")
        if fid:
            with st.spinner(f"📊 UFCStats for {name}"):
                uf[name] = fetch_ufcstats(fid)
        else:
            uf[name] = {}

    # Odds for all fights
    labels = [f"{f['fighter_a']} vs {f['fighter_b']}" for f in event_data["fight_card"]]
    with st.spinner("💰 Fetching betting odds..."):
        odds = batch_odds_lookup(labels)["odds"]

    # Merge data
    merged = {}
    for fight in event_data["fight_card"]:
        A = fight["fighter_a"]
        B = fight["fighter_b"]
        label = f"{A} vs {B}"
        fight_odds = odds.get(label, {})

        merged[label] = {
            A: merge_fighter_profile(A, meta.get(A, {}), tap.get(A, []), sd.get(A, []), uf.get(A, {}), fight_odds),
            B: merge_fighter_profile(B, meta.get(B, {}), tap.get(B, []), sd.get(B, []), uf.get(B, {}), fight_odds),
            "odds": fight_odds
        }

    return merged


# -----------------------------------------------------
# FINAL CARD ANALYSIS
# -----------------------------------------------------
def run_final_analysis(merged, event_data):
    payload = {
        "event": event_data,
        "merged_fighters": merged
    }

    prompt = f"""
Use the following dataset to produce full fight analysis:

{json.dumps(payload, indent=2)}

Instructions:
{analysis_prompt}
"""

    with st.spinner("🧠 Generating elite analysis..."):
        return call_gpt(prompt)


# -----------------------------------------------------
# UI — SINGLE BUTTON
# -----------------------------------------------------
st.subheader("🔥 Analyze the next UFC event automatically")

if st.button("Analyze Next UFC Event"):
    if not usage_ok():
        st.error("Daily usage limit reached.")
        st.stop()

    # 1. Get next UFC event (UFCStats scrape)
    with st.spinner("📅 Fetching next UFC event..."):
        event_data = get_next_ufc_event()

    if "error" in event_data:
        st.error(event_data["error"])
        st.stop()

    st.markdown(f"### {event_data['event_name']}")
    st.write(f"📍 {event_data['location']}")
    st.write(f"📅 {event_data['event_date']}")
    st.divider()

    # 2. Process fighters
    merged = process_fighters(event_data)

    # 3. Final analysis
    analysis = run_final_analysis(merged, event_data)

    st.markdown("## 📘 Full Fight Card Analysis")
    st.markdown(analysis)
