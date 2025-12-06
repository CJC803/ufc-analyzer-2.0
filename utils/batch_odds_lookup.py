from utils.openai_client import client
import time
import json

def batch_odds_lookup(fights):
    prompt = f"""
Retrieve betting odds for ALL fights below.

For each fight return:
- Fighter A moneyline
- Fighter B moneyline
- Implied prob A
- Implied prob B
- Odds source

Strict JSON:
{
  "odds": {
    "A vs B": {
      "fighter_a": "",
      "fighter_b": "",
      "implied_a": 0,
      "implied_b": 0,
      "source": ""
    }
  }
}

Fights:
{fights}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    time.sleep(0.4)
    return json.loads(res.choices[0].message.content)
