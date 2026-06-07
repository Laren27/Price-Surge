# scheduler.py
import urllib.request
import schedule
import time
import subprocess
import json
import os
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER      = PROJECT_ROOT / "src" / "scraping" / "zomato_scraper.py"
COOKIES_FILE = PROJECT_ROOT / "zomato_cookies.json"
LOG_FILE     = PROJECT_ROOT / "logs" / "scheduler.log"

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SCRAPE_INTERVAL_HOURS = 2
START_HOUR            = 10   # 10:00 AM
END_HOUR              = 23   # exit after 23:00
END_MINUTE            = 0

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
# LOGGER
# ─────────────────────────────────────────────
def log(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

def check_internet(retries=10, wait_seconds=60):
    """
    Checks internet every 60 seconds for up to 10 minutes.
    If connection restored within that window, proceeds normally.
    If still down after 10 minutes, skips the run.
    """
    for attempt in range(1, retries + 1):
        try:
            urllib.request.urlopen('https://www.google.com', timeout=5)
            if attempt > 1:
                log(f"[OK] Internet restored on attempt {attempt} — proceeding")
            return True
        except Exception:
            log(f"[WARN] No internet — attempt {attempt}/{retries}, retrying in {wait_seconds}s")
            time.sleep(wait_seconds)

    log("[FAIL] Internet still down after 10 minutes — skipping this run")
    return False

# ─────────────────────────────────────────────
# TIME WINDOW HELPERS
# ─────────────────────────────────────────────
def is_within_allowed_hours():
    """Returns True if current time is between 10am and 10pm."""
    now = datetime.now()
    return START_HOUR <= now.hour < (END_HOUR - 1)

def should_exit():
    """Returns True if past 23:00 — time to shut down."""
    now = datetime.now()
    return now.hour > END_HOUR or (now.hour == END_HOUR and now.minute >= END_MINUTE)

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
# GUARDED SCRAPE JOB
# Wraps scrape_job() with time window check
# This is what schedule calls every 2 hours
# ─────────────────────────────────────────────
def scrape_job_guarded():
    if should_exit():
        log("Past 23:00 — no more scrapes today.")
        return
    if not is_within_allowed_hours():
        log(f"Skipping — outside window ({START_HOUR}:00 AM to {END_HOUR - 1}:00 PM)")
        return
    scrape_job()

# ─────────────────────────────────────────────
# ONE-SHOT JOB FOR 10AM WHEN STARTED EARLY
# ─────────────────────────────────────────────
def scrape_job_once_at_ten():
    scrape_job()
    return schedule.CancelJob  # fires once then removes itself

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log("Scheduler started")
    log(f"   Scraper  : {SCRAPER}")
    log(f"   Cookies  : {COOKIES_FILE}")
    log(f"   Log      : {LOG_FILE}")
    log(f"   Window   : {START_HOUR}:00 AM to {END_HOUR - 1}:00 PM")
    log(f"   Interval : every {SCRAPE_INTERVAL_HOURS} hours")

    now = datetime.now()

    if should_exit():
        # Started after 11pm — nothing to do today
        log("Started after 23:00 — nothing to do today. Exiting.")
        exit(0)

    elif not is_within_allowed_hours():
        # Started before 10am — wait and pin first scrape at exactly 10:00
        log(f"Started before {START_HOUR}:00 AM — first scrape pinned at 10:00 AM.")
        schedule.every().day.at("10:00").do(scrape_job_once_at_ten)
        schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scrape_job_guarded)
        log(f"Rhythm: 10:00 AM, 12:00 PM, 2:00 PM, 4:00 PM ... until {END_HOUR - 1}:00 PM")

    else:
        # Started inside window — scrape immediately then every 2 hours
        log("Started inside window — running initial scrape now.")
        scrape_job()
        schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scrape_job_guarded)
        next_scrape = now + timedelta(hours=SCRAPE_INTERVAL_HOURS)
        log(f"Next scrape at approximately {next_scrape.strftime('%I:%M %p')}")

    log("Scheduler is running. Press Ctrl+C to stop.")

    last_reminder = datetime.now()

    while True:
        schedule.run_pending()

        now = datetime.now()

        # Auto exit after 23:00
        if should_exit():
            log("23:00 reached — scraping window closed. Exiting.")
            break

        # Countdown reminder every 20 minutes
        next_run = schedule.next_run()
        minutes_since_reminder = (now - last_reminder).seconds // 60

        if minutes_since_reminder >= 20:
            if next_run:
                remaining    = next_run - now
                total_secs   = int(remaining.total_seconds())
                hours_left   = total_secs // 3600
                minutes_left = (total_secs % 3600) // 60
                if is_within_allowed_hours():
                    log(f"Next scrape in {hours_left}h {minutes_left}m")
                else:
                    log(f"Waiting for 10:00 AM — starts in {hours_left}h {minutes_left}m")
            last_reminder = now

        time.sleep(60)

    log("Scheduler exited cleanly.")