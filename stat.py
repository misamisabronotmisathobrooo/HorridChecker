import requests
import threading
import time
import sys
import random
from queue import Queue

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1508590349713408231/CIljNz9hoywwrkH9ZJ7cjWVwUi5gogPNdGlWXzYucncqQb13qZZpB6D-Vi6wCSaeZ4WT"

# safer settings
THREADS = 1
COOLDOWN_MIN = 7
COOLDOWN_MAX = 16
MAX_RETRIES = 5

request_lock = threading.Lock()
checked_lock = threading.Lock()
checked = set()
names_queue = Queue()

# persistent session
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json"
})

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

def random_delay():
    delay = random.uniform(COOLDOWN_MIN, COOLDOWN_MAX)
    log(f"[SLEEP] {delay:.2f}s")
    time.sleep(delay)

log("[INIT] Username checker started")

# Load names from names.txt
with open("names.txt", "r", encoding="utf-8") as f:
    for line in f:
        name = line.strip()
        if name:
            names_queue.put(name)

def send_webhook(name):
    if not WEBHOOK:
        return
    try:
        session.post(
            WEBHOOK,
            json={
                "content": f"available: `{name}` @everyone",
                "allowed_mentions": {"parse": ["everyone"]}
            },
            timeout=10
        )
        log(f"[WEBHOOK] Sent hit for {name}")
    except Exception as e:
        log(f"[WEBHOOK ERROR] {e}")

def check(name):
    retries = 0
    while retries < MAX_RETRIES:
        random_delay()
        try:
            log(f"[CHECKING] {name}")
            r = session.post(
                API,
                json={"username": name},
                timeout=15
            )
            log(f"[RESPONSE] {name} -> {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                if data.get("taken", True):
                    log(f"[TAKEN] {name}")
                else:
                    log(f"[OPEN] {name}")
                    with open("hits.txt", "a", encoding="utf-8") as f:
                        f.write(name + "\n")
                    log(f"[SAVED] {name} -> hits.txt")
                    send_webhook(name)
                return
            elif r.status_code == 429:
                try:
                    retry_after = r.json().get("retry_after", 10)
                except:
                    retry_after = 10
                with request_lock:
                    log(f"[RATE LIMITED] Sleeping for {retry_after}s")
                time.sleep(float(retry_after) + random.uniform(1, 3))
                retries += 1
                log(f"[RETRY] {name} ({retries}/{MAX_RETRIES})")
            else:
                log(f"[ERROR] {name} -> HTTP {r.status_code}")
                return

        except Exception as e:
            log(f"[REQUEST ERROR] {name} -> {e}")
            retries += 1
            backoff = (2 ** retries) + random.uniform(0.5, 2)
            log(f"[BACKOFF] Sleeping {backoff:.2f}s")
            time.sleep(backoff)

    log(f"[GAVE UP] {name}")

def worker():
    while True:
        try:
            if names_queue.empty():
                log("[DONE] Queue empty, worker exiting")
                break
            name = names_queue.get()
            if name in checked:
                names_queue.task_done()
                continue

            with checked_lock:
                checked.add(name)

            check(name)
            names_queue.task_done()
            log(f"[TOTAL CHECKED] {len(checked)}")
        except Exception as e:
            log(f"[WORKER ERROR] {e}")
            time.sleep(5)

# Start threads
threads = []
log(f"[START] Launching {THREADS} thread(s)")
for i in range(THREADS):
    t = threading.Thread(target=worker, name=f"worker-{i}", daemon=True)
    t.start()
    log(f"[THREAD STARTED] worker-{i}")
    threads.append(t)

for t in threads:
    t.join()

log("[DONE] All workers finished")
