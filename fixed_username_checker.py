import requests
import sys
import os
import time
import string
from queue import Queue

# ================== CONFIGURATION ==================
API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1519504577173651466/6yYRuvHpdlP4-MxFMxWwyNhPA1j6RgUnlYox21o5PECB-_95S4EU2_OqYHPYv_tWKXfP"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_WORKFLOW = "checker.yml"

# <<< EDIT YOUR TARGET NAMES HERE >>>
CHARS = string.ascii_lowercase + string.digits + "._"

def generate_username(length=4):
    while True:
        name = ''.join(random.choice(CHARS) for _ in range(length))

        # Prevent invalid usernames
        if (
            name.startswith((".", "_")) or
            name.endswith((".", "_")) or
            ".." in name or
            "__" in name
        ):
            continue

        return name

CHECK_INTERVAL = 2  # Seconds to wait between full check cycles (recommended: 3-10)
# ===================================================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json"
})

def log(msg):
    print(msg, flush=True)

def send_webhook(name):
    if not WEBHOOK:
        return
    try:
        payload = {
            "content": f"✅ **Available Username Found!**\n`{name}`\n@everyone",
            "allowed_mentions": {"parse": ["everyone"]}
        }
        response = session.post(WEBHOOK, json=payload, timeout=10)
        if response.status_code in (200, 204):
            log(f"[WEBHOOK] ✅ Sent hit: {name}")
        else:
            log(f"[WEBHOOK] Failed: {response.status_code}")
    except Exception as e:
        log(f"[WEBHOOK ERROR] {e}")

def trigger_new_workflow_run():
    if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW]):
        return False
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
            return True
    except Exception as e:
        log(f"[GITHUB] Error: {e}")
    return False

log("[INIT] Fixed username checker started")
log(f"[TARGETS] Monitoring {len(name)} username(s): {name}")

def check(name):
    try:
        log(f"[CHECKING] {name}")
        r = session.post(API, json={"username": name}, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            if not data.get("taken", True):
                log(f"[OPEN] ✅ {name} IS AVAILABLE!")
                send_webhook(name)
                with open("hits.txt", "a", encoding="utf-8") as f:
                    f.write(name + "\n")
                return True  # Found available
            else:
                log(f"[TAKEN] {name}")
        elif r.status_code == 429:
            log("[RATE LIMITED] → Triggering new workflow run...")
            trigger_new_workflow_run()
            log("[EXIT] Exiting current run.")
            sys.exit(0)
        else:
            log(f"[ERROR] HTTP {r.status_code}")
    except Exception as e:
        log(f"[ERROR] {e}")
    return False

# Main loop - checks your names repeatedly
cycle = 0
while True:
    cycle += 1
    log(f"\n[ CYCLE {cycle} ] Starting check round...")
    
    name = generate_username()
    check(name)
    time.sleep(1)  # Small delay between individual checks
    
    log(f"[CYCLE {cycle}] Completed. Waiting {CHECK_INTERVAL} seconds...")
    time.sleep(CHECK_INTERVAL)
