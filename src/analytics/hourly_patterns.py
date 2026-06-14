# src/analytics/hourly_patterns.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'hourly_patterns'

HOURLY_OVERALL_QUERY = """
    SELECT
        hours.hour_of_day,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg ON hours.hour_of_day = chg.hour_of_day
    GROUP BY hours.hour_of_day
    ORDER BY hours.hour_of_day;
"""

HOURLY_PER_RESTAURANT_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category,
        hours.hour_of_day,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    CROSS JOIN (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
       AND base.restaurant_category = chg.restaurant_category
       AND hours.hour_of_day = chg.hour_of_day
    GROUP BY base.restaurant, base.restaurant_category, hours.hour_of_day
    ORDER BY base.restaurant, hours.hour_of_day;
"""

HOURLY_PEAK_PER_RESTAURANT_QUERY = """
    WITH ranked AS (
        SELECT
            restaurant,
            restaurant_category,
            hour_of_day,
            avg_price_change_pct,
            ROW_NUMBER() OVER (
                PARTITION BY restaurant, restaurant_category
                ORDER BY avg_price_change_pct DESC
            ) AS rn
        FROM (
            SELECT
                base.restaurant,
                base.restaurant_category,
                hours.hour_of_day,
                COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
            FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
            CROSS JOIN (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
            LEFT JOIN v_price_changes chg
                ON base.restaurant = chg.restaurant
               AND base.restaurant_category = chg.restaurant_category
               AND hours.hour_of_day = chg.hour_of_day
            GROUP BY base.restaurant, base.restaurant_category, hours.hour_of_day
        ) sub
    )
    SELECT restaurant, restaurant_category,
           hour_of_day AS peak_hour,
           avg_price_change_pct AS peak_change_pct
    FROM ranked WHERE rn = 1
    ORDER BY peak_change_pct DESC;
"""

PEAK_OFFPEAK_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category,
        CASE
            WHEN hours.hour_of_day IN (12, 13) THEN 'Lunch Peak'
            WHEN hours.hour_of_day IN (19, 20) THEN 'Dinner Peak'
            WHEN hours.hour_of_day IN (10, 11) THEN 'Morning Off-Peak'
            WHEN hours.hour_of_day IN (14, 15, 16, 17, 18) THEN 'Afternoon Off-Peak'
            WHEN hours.hour_of_day IN (21, 22) THEN 'Late Night Off-Peak'
            ELSE 'Other'
        END AS time_window,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS avg_price_change_pct
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    CROSS JOIN (SELECT DISTINCT hour_of_day FROM v_analysis_base) hours
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
       AND base.restaurant_category = chg.restaurant_category
       AND hours.hour_of_day = chg.hour_of_day
    GROUP BY base.restaurant, base.restaurant_category, time_window
    ORDER BY base.restaurant, avg_price_change_pct DESC;
"""

def fetch(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("Q7 — Clean Hourly Pattern Analysis")
    print("=" * 60)

    print("\n[1] Fetching hourly overall market metrics...")
    hourly_overall = fetch(HOURLY_OVERALL_QUERY)

    print("[2] Fetching hourly per-restaurant metrics...")
    hourly_per_restaurant = fetch(HOURLY_PER_RESTAURANT_QUERY)

    print("[3] Fetching peak hour per restaurant...")
    hourly_peak = fetch(HOURLY_PEAK_PER_RESTAURANT_QUERY)

    print("[4] Fetching peak vs off-peak window metrics...")
    peak_offpeak = fetch(PEAK_OFFPEAK_QUERY)

    print("\n── Hourly Overall (Market) ──")
    print(hourly_overall.to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hourly_overall.to_csv(OUT_DIR / 'hourly_overall.csv', index=False)
    hourly_per_restaurant.to_csv(OUT_DIR / 'hourly_per_restaurant.csv', index=False)
    hourly_peak.to_csv(OUT_DIR / 'hourly_peak_per_restaurant.csv', index=False)
    peak_offpeak.to_csv(OUT_DIR / 'peak_offpeak.csv', index=False)

    print("\n[5] Syncing all hourly tables to database...")
    engine = get_engine()

    hourly_overall.to_sql('analytics_hourly_overall', con=engine, if_exists='replace', index=False)
    hourly_per_restaurant.to_sql('analytics_hourly_per_restaurant', con=engine, if_exists='replace', index=False)
    hourly_peak.to_sql('analytics_hourly_peak_restaurant', con=engine, if_exists='replace', index=False)
    peak_offpeak.to_sql('analytics_peak_offpeak', con=engine, if_exists='replace', index=False)

    print("✅ Successfully updated all hourly analytics tables.")
    print("=" * 60)