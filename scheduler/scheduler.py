# scheduler.py

import schedule
import time
import subprocess
import json
import os
import importlib.util
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER      = PROJECT_ROOT / "src" / "scraping" / "zomato_scraper.py"
COOKIES_FILE = PROJECT_ROOT / "zomato_cookies.json"
LOG_FILE     = PROJECT_ROOT / "logs" / "scheduler.log"

# ─────────────────────────────────────────────
# LOAD WEATHER MODULE
# ─────────────────────────────────────────────
def load_weather_module():
    spec = importlib.util.spec_from_file_location(
        "weather",
        str(PROJECT_ROOT / "src" / "scraping" / "weather.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ─────────────────────────────────────────────
# LOAD DATABASE MODULE
# ─────────────────────────────────────────────
def load_db_module():
    spec = importlib.util.spec_from_file_location(
        "database",
        str(PROJECT_ROOT / "src" / "scraping" / "database.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_weather        = load_weather_module()
fetch_weather   = _weather.fetch_weather
save_weather    = _weather.save_weather

_db             = load_db_module()
save_weather_db = _db.save_weather_db

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SCRAPE_INTERVAL_HOURS = 2

# ─────────────────────────────────────────────
# LOGGER
# ─────────────────────────────────────────────
def log(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

# ─────────────────────────────────────────────
# COOKIE VALIDATOR
# ─────────────────────────────────────────────
def check_cookies_valid():
    try:
        with open(COOKIES_FILE) as f:
            saved_cookies = json.load(f)
    except FileNotFoundError:
        log("[FAIL] zomato_cookies.json not found")
        return False

    now = datetime.now().timestamp()

    key_cookies = [c for c in saved_cookies if
                   c.get("name", "").startswith("zl") or
                   c.get("name", "") == "PHPSESSID" or
                   c.get("name", "") == "zomato_user"]

    if not key_cookies:
        log("[FAIL] No session cookies found in file")
        return False

    for cookie in key_cookies:
        expires = cookie.get("expires", -1)
        if expires == -1:
            continue
        if expires < now:
            log(f"[FAIL] Cookie '{cookie['name']}' expired at {datetime.fromtimestamp(expires)}")
            return False

    log(f"[OK] Found {len(key_cookies)} valid session cookies")
    return True

# ─────────────────────────────────────────────
# SCRAPE JOB
# ─────────────────────────────────────────────
def scrape_job():
    log("=" * 50)
    log("Starting scheduled scrape run...")

    # ✅ Generate session ID once — shared by weather and all restaurants
    scrape_session_id = datetime.now().strftime("%Y%m%d_%H%M")
    log(f"Session ID: {scrape_session_id}")

    # Step 1: Check cookies file exists
    if not COOKIES_FILE.exists():
        log("[WARN] COOKIES MISSING — run src/scraping/save_cookies.py to fix")
        log("Skipping this run. Will try again in 2 hours.")
        log("=" * 50)
        return

    # Step 2: Validate cookies
    log("Checking cookie validity...")
    if not check_cookies_valid():
        log("[WARN] COOKIES EXPIRED — Zomato session ended")
        log("ACTION NEEDED: Open a new terminal and run: python src/scraping/save_cookies.py")
        log("Skipping this run. Will try again in 2 hours.")
        log("=" * 50)
        return

    log("[OK] Cookies valid — fetching weather...")

    # Step 3: Fetch and save weather with session ID
    weather = fetch_weather()
    if weather:
        weather["scrape_session_id"] = scrape_session_id  # ✅ attach before saving
        save_weather(weather)                              # CSV
        save_weather_db(weather)                           # database
        log(f"[OK] Weather: {weather['condition']} {weather['temperature']}C  Rainy: {weather['is_rainy']}")
    else:
        log("[WARN] Weather fetch failed — skipping weather for this run")

    # Step 4: Run the scraper passing session ID as environment variable
    # The scraper reads this from env so it uses the same session ID
    log("Starting scraper...")
    try:
        start_time = datetime.now()

        result = subprocess.run(
            ["python", str(SCRAPER)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3600,
            env={
                **os.environ,
                "PYTHONIOENCODING":  "utf-8",
                "SCRAPE_SESSION_ID": scrape_session_id  # ✅ pass to scraper
            }
        )

        duration = (datetime.now() - start_time).seconds // 60

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                log(f"  [scraper] {line}")

        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                log(f"  [error] {line}")

        if result.returncode == 0:
            log(f"[OK] Scrape completed in {duration} minutes")
        else:
            log(f"[FAIL] Scraper exited with error code {result.returncode}")

    except subprocess.TimeoutExpired:
        log("[FAIL] Scraper timed out after 1 hour — killed")
    except Exception as e:
        log(f"[FAIL] Failed to run scraper: {e}")

    log("=" * 50)

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log("Scheduler started")
    log(f"   Scraper  : {SCRAPER}")
    log(f"   Cookies  : {COOKIES_FILE}")
    log(f"   Log      : {LOG_FILE}")
    log(f"   Interval : every {SCRAPE_INTERVAL_HOURS} hours")

    log("Running initial scrape on startup...")
    scrape_job()

    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scrape_job)

    log(f"Next run scheduled in {SCRAPE_INTERVAL_HOURS} hours")
    log("Scheduler is running. Keep this terminal open.")
    log("Press Ctrl+C to stop.")

    last_reminder = datetime.now()

    while True:
        schedule.run_pending()

        now      = datetime.now()
        next_run = schedule.next_run()

        minutes_since_reminder = (now - last_reminder).seconds // 60
        if minutes_since_reminder >= 20:
            remaining    = next_run - now
            total_secs   = int(remaining.total_seconds())
            hours_left   = total_secs // 3600
            minutes_left = (total_secs % 3600) // 60
            log(f"Next scrape in {hours_left}h {minutes_left}m")
            last_reminder = now

        time.sleep(60)