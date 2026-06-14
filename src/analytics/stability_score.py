# src/analytics/stability_score.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'stability_score'

STABILITY_QUERY = """
    SELECT
        base.restaurant,
        base.restaurant_category,
        COUNT(chg.item_name)::INT AS price_change_events,
        COALESCE(ROUND(STDDEV(chg.pct_change)::NUMERIC, 4), 0.0) AS cv_pct,
        COALESCE(ROUND(AVG(chg.new_price)::NUMERIC, 2), 0.0) AS avg_price
    FROM (SELECT DISTINCT restaurant, restaurant_category FROM v_analysis_base) base
    LEFT JOIN v_price_changes chg
        ON base.restaurant = chg.restaurant AND base.restaurant_category = chg.restaurant_category
    GROUP BY base.restaurant, base.restaurant_category;
"""

def fetch(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

def normalize_series(series):
    max_val = series.max()
    if max_val == 0:
        return series * 0
    return (series / max_val) * 100

if __name__ == "__main__":
    print("=" * 60)
    print("Q6 — Clean Stability Score & Volatility")
    print("=" * 60)

    results = fetch(STABILITY_QUERY)
    results['pvs_normalized'] = normalize_series(results['price_change_events']).round(2)

    print("\n── Stability Rankings ──")
    print(results.sort_values('pvs_normalized', ascending=False).to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'stability_score_results.csv', index=False)

    engine = get_engine()
    results.to_sql(
        'analytics_stability_score',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_stability_score table.")
    print("=" * 60)