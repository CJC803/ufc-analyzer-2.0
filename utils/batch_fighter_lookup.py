from utils.openai_client import client
import time
import json

def batch_fighter_lookup(fighter_names):
    prompt = f"""
Retrieve metadata for all fighters. Return structured JSON.

For each fighter, retrieve:
- Tapology URL
- Sherdog URL
- UFCStats ID
- ESPN Profile
- Wikipedia URL
- Age
- Height
- Reach
- Stance
- Weight class
- Team/gym
- Nickname

Elite Analytics:
- Stylistic cluster label
- Striker/Grappler ratio
- Finishing reliability score (0–100)
- Fight IQ estimate (0–100)
- Gas tank grade (A–F)
- Durability grade (A–F)
- Momentum score (0–100)
- Prospect grade (0–100)
- Risk flags (weight cuts, layoffs, chin issues)

Return strict JSON:
{
  "fighters": {
    "Name": {
      "tapology_url": "",
      "sherdog_url": "",
      "ufcstats_id": "",
      "espn_url": "",
      "wiki_url": "",
      "age": "",
      "height": "",
      "reach": "",
      "stance": "",
      "gym": "",
      "nickname": "",
      "weight_class": "",
      "stylistic_cluster": "",
      "striker_grappler_ratio": "",
      "finishing_reliability": 0,
      "fight_iq": 0,
      "gas_tank_grade": "",
      "durability_grade": "",
      "momentum_score": 0,
      "prospect_grade": 0,
      "risk_flags": []
    }
  }
}

Fighters:
{fighter_names}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    time.sleep(0.4)
    return json.loads(res.choices[0].message.content)
