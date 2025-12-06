from utils.openai_client import client
import json
import time

def batch_tapology_histories(fighters):
    prompt = f"""
Retrieve FULL Tapology fight histories for the fighters below.

Return JSON ONLY:
{
  "fighters": {
    "Name": [
      {"result": "", "opponent": "", "method": "", "event": "", "date": "", "round": "", "time": ""}
    ]
  }
}

Fighters:
{fighters}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    time.sleep(0.4)
    return json.loads(res.choices[0].message.content)
