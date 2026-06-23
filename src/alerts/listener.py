# src/alerts/listener.py
# ─────────────────────────────────────────────
# Polls Telegram for incoming commands and responds.
# Runs as a daemon thread inside scheduler.py.
# Commands: /ping /status /last /next /logs
# ─────────────────────────────────────────────

import requests
import os
import json
import time
import urllib3
from datetime import datetime
from pathlib import Path

os.environ.pop("REQUESTS_CA_BUNDLE", None)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID    = int(os.getenv("TELEGRAM_CHAT_ID"))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE   = PROJECT_ROOT / "data" / "state.json"

SCRAPE_TIMES = ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]

# ─────────────────────────────────────────────
# STATE HELPERS
# ─────────────────────────────────────────────

def read_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ─────────────────────────────────────────────
# SEND REPLY
# ─────────────────────────────────────────────

def send_reply(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10, verify=False)
    except Exception as e:
        print(f"[LISTENER] Failed to send reply: {e}")


# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

def handle_ping():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_reply(
        f"🟢 <b>Pong!</b>\n"
        f"————————————————————\n"
        f"• Bot is alive and listening\n"
        f"• Checked at: {now}"
    )


def handle_status():
    state = read_state()
    if not state:
        send_reply("⚠️ No state data found yet — scraper hasn't run since bot started.")
        return

    last_status   = state.get("last_status", "Unknown")
    last_time     = state.get("last_scrape_time", "—")
    last_session  = state.get("last_session_id", "—")
    last_duration = state.get("last_duration_minutes", "—")

    emoji = "✅" if last_status == "success" else "❌"

    send_reply(
        f"📊 <b>Scraper Status</b>\n"
        f"————————————————————\n"
        f"• Last Run: {emoji} {last_status.upper()}\n"
        f"• Session ID: {last_session}\n"
        f"• Completed At: {last_time}\n"
        f"• Duration: {last_duration} minutes\n"
        f"• Restaurants: 19 | Categories: 5"
    )


def handle_last():
    state = read_state()
    if not state:
        send_reply("⚠️ No session data available yet.")
        return

    last_status      = state.get("last_status", "Unknown")
    last_session     = state.get("last_session_id", "—")
    last_time        = state.get("last_scrape_time", "—")
    last_duration    = state.get("last_duration_minutes", "—")
    restaurants      = state.get("restaurants_scraped", "—")
    error_type       = state.get("last_error_type", None)

    emoji = "✅" if last_status == "success" else "❌"

    text = (
        f"🕘 <b>Last Scrape Session</b>\n"
        f"————————————————————\n"
        f"• Status: {emoji} {last_status.upper()}\n"
        f"• Session ID: {last_session}\n"
        f"• Completed At: {last_time}\n"
        f"• Duration: {last_duration} minutes\n"
        f"• Restaurants Scraped: {restaurants}/19"
    )

    if error_type:
        text += f"\n• Error: {error_type}"

    send_reply(text)


def handle_next():
    now  = datetime.now()
    text = ""

    next_slot = next(
        (t for t in SCRAPE_TIMES if int(t.split(":")[0]) > now.hour),
        None
    )

    if not next_slot:
        send_reply(
            f"🌙 <b>No More Slots Today</b>\n"
            f"————————————————————\n"
            f"• All slots completed for today.\n"
            f"• Next window opens at 10:00 AM tomorrow."
        )
        return

    slot_hour, slot_min = map(int, next_slot.split(":"))
    next_dt      = now.replace(hour=slot_hour, minute=slot_min, second=0, microsecond=0)
    mins_left    = int((next_dt - now).total_seconds() // 60)
    hours_left   = mins_left // 60
    minutes_left = mins_left % 60

    countdown = f"{hours_left}h {minutes_left}m" if hours_left else f"{minutes_left}m"

    remaining_slots = [t for t in SCRAPE_TIMES if int(t.split(":")[0]) >= slot_hour]

    send_reply(
        f"⏰ <b>Next Scheduled Scrape</b>\n"
        f"————————————————————\n"
        f"• Next Slot: {next_slot}\n"
        f"• Time Until Scrape: {countdown}\n"
        f"• Remaining Slots Today: {', '.join(remaining_slots)}"
    )


def handle_logs():
    state = read_state()
    log_entries = state.get("recent_logs", [])

    if not log_entries:
        send_reply("📋 No log entries recorded yet.")
        return

    lines = ["📋 <b>Last 5 Alert Log</b>\n————————————————————"]
    for i, entry in enumerate(reversed(log_entries[-5:]), 1):
        emoji  = "✅" if entry.get("status") == "success" else "❌"
        ts     = entry.get("time", "—")
        dur    = entry.get("duration_minutes", "—")
        sid    = entry.get("session_id", "—")
        lines.append(f"\n<b>#{i}</b> {emoji} {ts}\n  Session: {sid} | Duration: {dur}m")

    send_reply("\n".join(lines))


# ─────────────────────────────────────────────
# COMMAND ROUTER
# ─────────────────────────────────────────────

COMMANDS = {
    "/ping":   handle_ping,
    "/status": handle_status,
    "/last":   handle_last,
    "/next":   handle_next,
    "/logs":   handle_logs,
}

def handle_update(update: dict):
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text    = message.get("text", "").strip().split("@")[0]  # strip bot username if present

    if chat_id != CHAT_ID:
        return  # ignore messages from other chats

    handler = COMMANDS.get(text)
    if handler:
        print(f"[LISTENER] Command received: {text}")
        handler()
    else:
        if text.startswith("/"):
            send_reply(
                f"❓ Unknown command: <code>{text}</code>\n\n"
                f"Available commands:\n"
                f"/ping — Check if bot is alive\n"
                f"/status — Current scraper status\n"
                f"/last — Last scrape session details\n"
                f"/next — Next scheduled scrape slot\n"
                f"/logs — Last 5 session log entries"
            )


# ─────────────────────────────────────────────
# POLLING LOOP (runs as daemon thread)
# ─────────────────────────────────────────────

def start_listener():
    print("[LISTENER] Command listener started — polling every 3s")
    offset = None

    while True:
        try:
            url    = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 2, "offset": offset}
            resp   = requests.get(url, params=params, timeout=10, verify=False)
            data   = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                handle_update(update)

        except Exception as e:
            print(f"[LISTENER] Poll error: {e}")

        time.sleep(3)
if __name__ == "__main__":
    start_listener()