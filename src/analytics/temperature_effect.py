# src/analytics/temperature_effect.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'temperature_effect'

TEMPERATURE_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category AS category,
        COUNT(CASE WHEN chg.temperature_band = 'Cool'   THEN 1 END)::INT AS cool_records,
        COUNT(CASE WHEN chg.temperature_band = 'Normal' THEN 1 END)::INT AS normal_records,
        COUNT(CASE WHEN chg.temperature_band = 'Hot'    THEN 1 END)::INT AS hot_records,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Hot'    THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_price_hot,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Normal' THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS avg_price_normal,
        COALESCE(ROUND(AVG(CASE WHEN chg.temperature_band = 'Hot'    THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS temp_effect_score
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category
    ORDER BY temp_effect_score DESC NULLS LAST;
"""

def fetch(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("Q3 — Clean Temperature Effect Analysis")
    print("=" * 60)

    print("\n[1] Pulling temperature-banded price changes from verified views...")
    results = fetch(TEMPERATURE_QUERY)

    results['significant'] = (
        results['hot_records'] + results['cool_records']
    ).apply(lambda x: x >= 3)

    results['verdict'] = results.apply(
        lambda r: 'Price rises in heat' if r['significant'] and r['temp_effect_score'] > 0
        else ('Price drops in heat'     if r['significant'] and r['temp_effect_score'] < 0
        else 'No significant change'),
        axis=1
    )

    print("\n── Temperature Effect Metrics ──")
    print(results.to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'temperature_effect_results.csv', index=False)

    print("\n[2] Syncing metrics to analytical table engine...")
    engine = get_engine()
    results.to_sql(
        'analytics_temperature_effect',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_temperature_effect table.")
    print("=" * 60)