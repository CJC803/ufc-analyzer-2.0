import time
import json
from openai import APIError, RateLimitError
from utils.openai_client import client


def gpt_safe_call(messages, model="gpt-4o-mini", temperature=0, max_retries=6):
    """
    A rate-limit-safe GPT call.
    Automatically retries on:
    - RateLimitError
    - APIError
    - transient network issues
    """

    delay = 1.8  # starting delay
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return res.choices[0].message.content

        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 1.7  # slow exponential backoff

        except APIError:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 1.7

    raise Exception("GPT call failed after all retries.")
