# src/alerts/telegram.py

import requests
import os
os.environ.pop("REQUESTS_CA_BUNDLE", None)  # remove PG's SSL override before any requests call
from dotenv import load_dotenv
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def alert_scrape_started(session_id: str, next_slot: str = None):
    """Alert D — sent at the moment a scrape cycle begins."""
    next_info = f"\n• Next Slot: {next_slot}" if next_slot else ""
    text = (
        f"🔄 <b>Scrape Cycle Started</b>\n"
        f"————————————————————\n"
        f"• Session ID: {session_id}\n"
        f"• Target: Bhubaneswar Market — 19 Restaurants\n"
        f"• Started At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"{next_info}"
    )
    send_message(text)


def send_message(text: str) -> bool:
    """
    Sends a plain text message to your Telegram chat.
    Returns True if successful, False if it failed.
    We return a bool instead of raising an exception because
    a failed alert should never crash the scraper itself.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("[ALERTS] Telegram credentials missing in .env — skipping alert.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"   # lets us use <b>bold</b> if we want later
    }

    try:
        response = requests.post(url, json=payload, timeout=10, verify=False)
        response.raise_for_status()  # raises an exception if status code is 4xx or 5xx
        return True
    except requests.exceptions.RequestException as e:
        # We print but don't crash — alert failure is not a scraper failure
        print(f"[ALERTS] Failed to send Telegram message: {e}")
        return False


# ── The three alert functions ─────────────────────────────────

def alert_scrape_success(duration_minutes: float, restaurants_scraped: int):
    """Alert A — sent after every clean scrape completion."""
    text = (
        f"✅ <b>Scrape Shift Completed Successfully</b>\n"
        f"————————————————————\n"
        f"• Target Area: Bhubaneswar Market\n"
        f"• Duration: {duration_minutes:.1f} minutes\n"
        f"• Observed Sessions: {restaurants_scraped}/19 Restaurants\n"
        f"• Status: Data successfully committed to PostgreSQL database."
    )
    send_message(text)


def alert_scrape_failure(error_type: str, traceback_snippet: str):
    """Alert B — sent when the scraper crashes."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"❌ <b>CRITICAL SYSTEM FAILURE: Scraper Crashed</b>\n"
        f"————————————————————\n"
        f"• Timestamp: {timestamp}\n"
        f"• Error Type: {error_type}\n"
        f"• Diagnostic Trace: {traceback_snippet[:300]}\n"
        f"• Action Required: Check server log context files immediately."
    )
    send_message(text)


def alert_no_internet():
    """Alert C — sent when network connectivity check fails."""
    text = (
        f"⚠️ <b>SYSTEM ALERT: Network Connection Offline</b>\n"
        f"————————————————————\n"
        f"• Status: Scrape shift aborted.\n"
        f"• Diagnosis: Host machine has no active internet access or request timed out.\n"
        f"• Mitigation: Will re-attempt connection on the next scheduled cron cycle."
    )
    send_message(text)

def alert_waiting_for_window(minutes_until_start: int):
    """Alert E — sent when scheduler starts outside the scraping window."""
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    first_scrape = datetime.now().replace(hour=10, minute=0, second=0).strftime("%Y-%m-%d %H:%M")
    text = (
        f"⏳ <b>Scheduler Started — Waiting for Window</b>\n"
        f"————————————————————\n"
        f"• Started At: {start_time}\n"
        f"• Current Status: Outside scraping window\n"
        f"• Minutes Until First Scrape: {minutes_until_start} minutes\n"
        f"• First Scrape At: {first_scrape}\n"
        f"• Scraping Window: 10:00 AM — 10:00 PM"
    )
    send_message(text)