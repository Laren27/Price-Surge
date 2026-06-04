# database.py

import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from dotenv import load_dotenv
import os

# ─────────────────────────────────────────────
# LOAD ENV
# ─────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "zomato_prices",
    "user":     "postgres",
    "password": os.getenv("POSTGRES_PASSWORD")
}

# ─────────────────────────────────────────────
# CONNECTION HELPER
# ─────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ─────────────────────────────────────────────
# CREATE TABLES
# ─────────────────────────────────────────────
def create_tables():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id                SERIAL PRIMARY KEY,
            restaurant        TEXT NOT NULL,
            category          TEXT,
            item_name         TEXT NOT NULL,
            price             INTEGER NOT NULL,
            scraped_at        TIMESTAMP NOT NULL,
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id                SERIAL PRIMARY KEY,
            city              TEXT NOT NULL,
            temperature       REAL,
            humidity          INTEGER,
            condition         TEXT,
            description       TEXT,
            wind_speed        REAL,
            is_rainy          BOOLEAN,
            recorded_at       TIMESTAMP NOT NULL,
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_scraped_at
        ON prices(scraped_at);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_restaurant
        ON prices(restaurant);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_session
        ON prices(scrape_session_id);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_weather_recorded_at
        ON weather(recorded_at);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_weather_session
        ON weather(scrape_session_id);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Tables created successfully")

# ─────────────────────────────────────────────
# SAVE PRICES
# ─────────────────────────────────────────────
def save_prices(data):
    if not data:
        return

    conn = get_connection()
    cur  = conn.cursor()

    rows = []
    for row in data:
        price_clean = int(str(row["price"]).replace("₹", "").strip())
        rows.append((
            row["restaurant"],
            row["category"],
            row["item_name"],
            price_clean,
            row["scraped_at"],
            row.get("scrape_session_id", None)
        ))

    execute_values(cur, """
        INSERT INTO prices
            (restaurant, category, item_name, price, scraped_at, scrape_session_id)
        VALUES %s
    """, rows)

    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] Saved {len(rows)} price rows to database")

# ─────────────────────────────────────────────
# SAVE WEATHER
# ─────────────────────────────────────────────
def save_weather_db(weather):
    if not weather:
        return

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        INSERT INTO weather
            (city, temperature, humidity, condition,
             description, wind_speed, is_rainy,
             recorded_at, scrape_session_id)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        weather["city"],
        weather["temperature"],
        weather["humidity"],
        weather["condition"],
        weather["description"],
        weather["wind_speed"],
        weather["is_rainy"],
        weather["recorded_at"],
        weather.get("scrape_session_id", None)
    ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] Weather saved to database: {weather['condition']} {weather['temperature']}C")

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Setting up database...")
    create_tables()
    print("Done. Tables ready in zomato_prices database.")