# src/analytics/hourly_patterns.py
#
# Q3 — Hourly Pricing Analysis
# Question : What time of day consistently produces the highest menu prices?
# Output   : Average price per hour across all restaurants and per restaurant
# Method   : GROUP BY hour_of_day, compute avg price, rank windows
#
# Run from anywhere:
#   python src/analytics/hourly_patterns.py

import pandas as pd
from pathlib import Path
import psycopg2
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine, save_df_to_db
# ─────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────

# Overall hourly pattern across all restaurants
HOURLY_OVERALL_QUERY = """
    SELECT
        hour_of_day,
        COUNT(*)                                        AS total_records,
        ROUND(AVG(price)::NUMERIC, 2)                   AS avg_price,
        ROUND(MIN(price)::NUMERIC, 2)                   AS min_price,
        ROUND(MAX(price)::NUMERIC, 2)                   AS max_price,
        ROUND(STDDEV(price)::NUMERIC, 2)                AS price_stddev
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY hour_of_day
    ORDER BY hour_of_day;
"""

# Hourly pattern per restaurant per category
HOURLY_PER_RESTAURANT_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        hour_of_day,
        COUNT(*)                                        AS total_records,
        ROUND(AVG(price)::NUMERIC, 2)                   AS avg_price
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY restaurant, restaurant_category, hour_of_day
    ORDER BY restaurant, hour_of_day;
"""

# Peak vs off-peak comparison
# Peak   : 1200–1400 (lunch), 1900–2100 (dinner)
# Off-peak: 1000–1200, 1400–1800, 2100–2200
PEAK_OFFPEAK_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        CASE
            WHEN hour_of_day IN (12, 13)        THEN 'Lunch Peak'
            WHEN hour_of_day IN (19, 20)        THEN 'Dinner Peak'
            WHEN hour_of_day IN (10, 11)        THEN 'Morning Off-Peak'
            WHEN hour_of_day IN (14, 15, 16, 17, 18) THEN 'Afternoon Off-Peak'
            WHEN hour_of_day IN (21, 22)        THEN 'Late Night Off-Peak'
            ELSE 'Other'
        END                                             AS time_window,
        COUNT(*)                                        AS total_records,
        ROUND(AVG(price)::NUMERIC, 2)                   AS avg_price
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY restaurant, restaurant_category, time_window
    ORDER BY restaurant, avg_price DESC;
"""

# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch(query):
    conn = get_connection()
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

# ─────────────────────────────────────────────
# CORE ANALYSIS
# ─────────────────────────────────────────────
def analyze_hourly(df_overall, df_per_restaurant):

    # ── Overall cheapest and most expensive windows ──
    cheapest_hour    = df_overall.loc[df_overall['avg_price'].idxmin()]
    most_expensive_hour = df_overall.loc[df_overall['avg_price'].idxmax()]

    print("\n── Overall Hourly Summary ──")
    print(df_overall.to_string(index=False))

    print(f"\n🟢 Cheapest window    : {int(cheapest_hour['hour_of_day']):02d}:00"
          f"  →  avg ₹{cheapest_hour['avg_price']}")
    print(f"🔴 Most expensive window : {int(most_expensive_hour['hour_of_day']):02d}:00"
          f"  →  avg ₹{most_expensive_hour['avg_price']}")

    # ── Per restaurant: which hour is their peak price hour ──
    print("\n── Peak Price Hour Per Restaurant ──")
    peak_per_restaurant = (
        df_per_restaurant
        .sort_values('avg_price', ascending=False)
        .groupby(['restaurant', 'restaurant_category'])
        .first()
        .reset_index()
        [['restaurant', 'restaurant_category', 'hour_of_day', 'avg_price']]
        .rename(columns={'hour_of_day': 'peak_hour', 'avg_price': 'peak_avg_price'})
        .sort_values('peak_avg_price', ascending=False)
    )
    print(peak_per_restaurant.to_string(index=False))

    return peak_per_restaurant

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df_overall, df_per_restaurant, df_peak_offpeak, df_peak_per_restaurant):
    out = ROOT_DIR / 'data' / 'processed' / 'hourly_patterns'
    out.mkdir(parents=True, exist_ok=True)

    df_overall.to_csv(out / 'hourly_overall.csv', index=False)
    df_per_restaurant.to_csv(out / 'hourly_per_restaurant.csv', index=False)
    df_peak_offpeak.to_csv(out / 'peak_offpeak.csv', index=False)
    df_peak_per_restaurant.to_csv(out / 'hourly_peak_per_restaurant.csv', index=False)

    print(f"\n✅ Results saved to {out}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q3 — Hourly Pricing Analysis")
    print("=" * 60)

    print("\n[1] Fetching data...")
    df_overall          = fetch(HOURLY_OVERALL_QUERY)
    df_per_restaurant   = fetch(HOURLY_PER_RESTAURANT_QUERY)
    df_peak_offpeak     = fetch(PEAK_OFFPEAK_QUERY)

    if df_overall.empty:
        print("⚠️  No data found. Check v_analysis_base.")
        sys.exit()

    print(f"    Hours covered   : {sorted(df_overall['hour_of_day'].tolist())}")
    print(f"    Restaurants     : {df_per_restaurant['restaurant'].nunique()}")

    print("\n[2] Running Analysis...")
    df_peak_per_restaurant = analyze_hourly(df_overall, df_per_restaurant)

    print("\n[3] Peak vs Off-Peak Summary:")
    print(df_peak_offpeak.to_string(index=False))

    save_results(df_overall, df_per_restaurant, df_peak_offpeak, df_peak_per_restaurant)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(df_overall,             'analytics_hourly_overall',         engine)
    save_df_to_db(df_per_restaurant,      'analytics_hourly_per_restaurant',  engine)
    save_df_to_db(df_peak_offpeak,        'analytics_peak_offpeak',           engine)
    save_df_to_db(df_peak_per_restaurant, 'analytics_hourly_peak_restaurant', engine)

    print("\n" + "=" * 60)