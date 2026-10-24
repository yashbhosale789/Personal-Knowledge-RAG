from dotenv import load_dotenv

load_dotenv()

import os
import threading
import time

import requests

API_KEY = os.environ["API_KEY"]
URL = "http://127.0.0.1:8000/query"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

results = {}


def fire(label, provider):
    body = {
        "query": f"What does the document say about vehicle maintenance? ({label})",
        "provider": provider,
        "return_contexts": False,
    }
    start = time.monotonic()
    resp = requests.post(URL, headers=HEADERS, json=body, timeout=120)
    elapsed = time.monotonic() - start
    results[label] = {"response": resp.json(), "elapsed": round(elapsed, 2)}


t1 = threading.Thread(target=fire, args=("A", "groq"))
t2 = threading.Thread(target=fire, args=("B", "gemini"))

t1.start()
t2.start()
t1.join()
t2.join()

for label, expected in [("A", "groq"), ("B", "gemini")]:
    entry = results[label]
    actual = entry["response"].get("provider")
    status = "OK" if actual == expected else "MISMATCH"
    print(
        f"Request {label}: expected={expected} actual={actual}  elapsed={entry['elapsed']}s  [{status}]"
    )
