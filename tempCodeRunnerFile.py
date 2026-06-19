# test_alert.py  (create this in your Price Surge/ root, delete after testing)

from src.alerts.telegram import alert_scrape_success, alert_scrape_failure, alert_no_internet

print("Sending Alert A...")
alert_scrape_success(duration_minutes=14.2, restaurants_scraped=19)

print("Sending Alert B...")
alert_scrape_failure(
    error_type="OperationalError",
    traceback_snippet="psycopg2.OperationalError: could not connect to server"
)

print("Sending Alert C...")
alert_no_internet()

print("Done — check Telegram.")