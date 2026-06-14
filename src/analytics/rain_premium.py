# src/analytics/rain_premium.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'rain_premium_results'

RAIN_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.is_rainy = TRUE THEN 1 END)::INT AS rainy_records,
        COUNT(CASE WHEN chg.is_rainy = FALSE THEN 1 END)::INT AS clear_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_rain,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = FALSE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_change_clear,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS rpi
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category
    ORDER BY rpi DESC NULLS LAST;
"""

def fetch(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("Q1 — Clean Rain Premium Index Analysis")
    print("=" * 60)

    results = fetch(RAIN_QUERY)

    results['significant'] = results['rainy_records'].apply(lambda x: x >= 5)
    results['verdict'] = results.apply(
        lambda r: 'Surge confirmed'     if r['significant'] and r['rpi'] > 0
        else ('Drop during rain'        if r['significant'] and r['rpi'] < 0
        else 'No significant change'),
        axis=1
    )

    print("\n── Rain Premium Metrics ──")
    print(results.to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'rain_premium_results.csv', index=False)

    engine = get_engine()
    results.to_sql(
        'analytics_rain_premium',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_rain_premium table.")
    print("=" * 60)