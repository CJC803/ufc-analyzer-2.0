# UFC Fight Card Analyzer (Elite Mode)

A Streamlit app that:
- Retrieves the next UFC event
- Gathers fighter metadata from GPT (batched)
- Pulls Tapology histories (batched)
- Scrapes Sherdog + UFCStats
- Retrieves odds for entire card in one GPT call
- Runs elite-level analysis on all matchups
- Generates 3 parlays (Safe, Value, Chaos)

## Deployment (Streamlit Cloud)
1. Upload repo to GitHub
2. Create Streamlit app
3. Set main file: main.py
4. Add secret:

OPENAI_API_KEY = "your-key"

5. Deploy

## Features
- Rate-limit safe (batch + caching)
- GPT-powered fighter vectors
- Elite Mode analytics
