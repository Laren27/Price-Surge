# src/analytics/category_sensitivity.py
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'category_sensitivity'

SENSITIVITY_QUERY = """
    SELECT
        base.dish_type,
        COUNT(chg.item_name)::INT AS total_change_events,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_rainy   = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS rpi,
        COALESCE(ROUND(AVG(CASE WHEN chg.is_weekend = TRUE THEN chg.pct_change END)::NUMERIC, 2), 0.0) AS wpi,
        COALESCE(ROUND(AVG(chg.pct_change)::NUMERIC, 2), 0.0) AS sensitivity_score
    FROM (SELECT DISTINCT dish_type FROM v_analysis_base WHERE dish_type != 'Other') base
    LEFT JOIN v_price_changes chg ON base.dish_type = chg.dish_type
    GROUP BY base.dish_type
    ORDER BY sensitivity_score DESC NULLS LAST;
"""

def fetch(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("Q5 — Clean Category Sensitivity Analysis")
    print("=" * 60)

    results = fetch(SENSITIVITY_QUERY)

    print("\n── Category Sensitivity Rankings ──")
    print(results.to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'category_sensitivity_results.csv', index=False)

    engine = get_engine()
    results.to_sql(
        'analytics_category_sensitivity',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_category_sensitivity table.")
    print("=" * 60)