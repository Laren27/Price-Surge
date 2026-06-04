# weather.py
# Fetches current weather for Bhubaneswar from OpenWeatherMap API.
# Saves to data/raw/weather_data.csv (append mode — same as prices).
#
# HOW IT WORKS:
# - Calls OpenWeatherMap's free "current weather" endpoint
# - Extracts temperature, humidity, condition, rain flag
# - Appends one row to weather_data.csv per call
# - Called by scheduler.py alongside the scraper

import requests
import csv
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    raise ValueError("[FAIL] OPENWEATHER_API_KEY not found in .env file")
    
CITY        = "Bhubaneswar"
UNITS       = "metric"                      # Celsius
CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "weather_data.csv"

# OpenWeatherMap free endpoint
URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units={UNITS}"

# ─────────────────────────────────────────────
# FETCH WEATHER
# ─────────────────────────────────────────────
def fetch_weather():
    """
    Calls OpenWeatherMap API and returns a clean dict.

    Raw API response looks like:
    {
        "main": {"temp": 32.5, "humidity": 85},
        "weather": [{"main": "Rain", "description": "moderate rain"}],
        "wind": {"speed": 4.2},
        "name": "Bhubaneswar"
    }
    We extract only what we need.
    """
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()      # raises error if status != 200
        data = response.json()

        condition   = data["weather"][0]["main"]          # "Rain", "Clear", "Clouds" etc
        description = data["weather"][0]["description"]   # "moderate rain", "clear sky" etc
        temperature = data["main"]["temp"]                # in Celsius
        humidity    = data["main"]["humidity"]            # percentage
        wind_speed  = data["wind"]["speed"]               # m/s
        is_rainy    = condition.lower() in (              # simple True/False flag
                        "rain", "drizzle",
                        "thunderstorm", "squall"
                      )

        return {
            "city":        CITY,
            "temperature": temperature,
            "humidity":    humidity,
            "condition":   condition,
            "description": description,
            "wind_speed":  wind_speed,
            "is_rainy":    is_rainy,
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    except requests.exceptions.Timeout:
        print("[FAIL] Weather API timed out")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[FAIL] Weather API HTTP error: {e}")
        return None
    except Exception as e:
        print(f"[FAIL] Weather fetch failed: {e}")
        return None

# ─────────────────────────────────────────────
# SAVE TO CSV
# ─────────────────────────────────────────────
def save_weather(weather_row):
    """
    Appends one weather row to weather_data.csv.
    Creates file with header if it doesn't exist yet.
    """
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "city", "temperature", "humidity",
            "condition", "description", "wind_speed",
            "is_rainy", "recorded_at", "scrape_session_id"  # ✅ added
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow(weather_row)

    print(f"[OK] Weather saved: {weather_row['condition']} "
          f"{weather_row['temperature']}C  "
          f"Humidity {weather_row['humidity']}%  "
          f"Rainy: {weather_row['is_rainy']}")

# ─────────────────────────────────────────────
# ENTRY POINT — run standalone to test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching weather for Bhubaneswar...")
    weather = fetch_weather()
    if weather:
        print(f"  Condition   : {weather['condition']} ({weather['description']})")
        print(f"  Temperature : {weather['temperature']}C")
        print(f"  Humidity    : {weather['humidity']}%")
        print(f"  Wind        : {weather['wind_speed']} m/s")
        print(f"  Is Rainy    : {weather['is_rainy']}")
        save_weather(weather)
    else:
        print("[FAIL] Could not fetch weather")