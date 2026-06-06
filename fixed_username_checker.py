import requests
import sys
import os
from queue import Queue

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1508590349713408231/CIljNz9hoywwrkH9ZJ7cjWVwUi5gogPNdGlWXzYucncqQb13qZZpB6D-Vi6wCSaeZ4WT"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_WORKFLOW = os.getenv("GITHUB_WORKFLOW")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json"
})

def log(msg):
    print(msg, flush=True)

def trigger_new_workflow_run():
    if not GITHUB_WORKFLOW:
        log(f"[GITHUB] GITHUB_WORKFLOW env var is empty!")
        return

    log(f"[GITHUB] Triggering workflow file: '{GITHUB_WORKFLOW}'")

    owner, repo = GITHUB_REPOSITORY.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        r = requests.post(url, json={"ref": "main"}, headers=headers, timeout=10)
        if r.status_code in (200, 204):
            log("[GITHUB] ✅ Successfully triggered new workflow run!")
        else:
            log(f"[GITHUB] Failed {r.status_code}: {r.text}")
    except Exception as e:
        log(f"[GITHUB] Error: {e}")

log("[INIT] Starting checker...")

# Load names
names_queue = Queue()
with open("names.txt", "r", encoding="utf-8") as f:
    for line in f:
        name = line.strip()
        if name:
            names_queue.put(name)

def check(name):
    try:
        log(f"[CHECKING] {name}")
        r = session.post(API, json={"username": name}, timeout=15)
        log(f"[RESPONSE] {name} -> {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            if not data.get("taken", True):
                log(f"[OPEN] {name}")
                with open("hits.txt", "a", encoding="utf-8") as f:
                    f.write(name + "\n")
                log(f"[SAVED] {name}")

        elif r.status_code == 429:
            log("[RATE LIMITED] → Triggering new run now...")
            trigger_new_workflow_run()
            log("[EXIT] Exiting so new run can start.")
            sys.exit(0)

        else:
            log(f"[ERROR] HTTP {r.status_code}")

    except Exception as e:
        log(f"[ERROR] {e}")

# Run
while not names_queue.empty():
    name = names_queue.get()
    check(name)

log("[DONE]")
