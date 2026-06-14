# src/analytics/weekend_premium.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'weekend_premium_results'

WPI_PREMIUM_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.is_weekend = TRUE THEN 1 END)::INT AS weekend_records,
        COUNT(CASE WHEN chg.is_weekend = FALSE THEN 1 END)::INT AS weekday_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_weekend,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = FALSE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_weekday,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS wpi
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant
       AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category
    ORDER BY wpi DESC;
"""

def fetch_data(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("Q4 — Clean Weekend Premium Analysis")
    print("=" * 60)

    print("\n[1] Pulling weekend adjustments directly from verified views...")
    results = fetch_data(WPI_PREMIUM_QUERY)

    results['significant'] = results['weekend_records'].apply(lambda x: x >= 3)
    results['verdict'] = results.apply(
        lambda r: 'Weekend premium confirmed' if r['significant'] and r['wpi'] > 0
        else ('Cheaper on weekends'           if r['significant'] and r['wpi'] < 0
        else 'No significant change'),
        axis=1
    )

    print("\n── Verified Weekend Premium Metrics ──")
    print(results.to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'weekend_premium_results.csv', index=False)

    print("\n[2] Syncing to analytical storage table...")
    engine = get_engine()
    results.to_sql(
        'analytics_weekend_premium',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_weekend_premium table.")
    print("=" * 60)