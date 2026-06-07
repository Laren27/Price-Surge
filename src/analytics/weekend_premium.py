# src/analytics/weekend_premium.py
#
# Q4 — Weekend Premium Analysis
# Question : Do restaurants charge more on weekends?
# Output   : Weekend Premium Index (WPI) per restaurant per category
# Formula  : WPI = (avg_price_weekend - avg_price_weekday) / avg_price_weekday × 100
# Test     : Mann-Whitney U (one-tailed) — p < 0.05 = significant premium
#
# Run from anywhere:
#   python src/analytics/weekend_premium.py

import pandas as pd
from scipy.stats import mannwhitneyu
from pathlib import Path
import psycopg2
import sys
import os
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine, save_df_to_db
# ─────────────────────────────────────────────
# QUERY
# ─────────────────────────────────────────────
QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        item_name,
        price,
        is_weekend,
        day_of_week,
        scraped_at
    FROM v_analysis_base
    WHERE price      IS NOT NULL
      AND is_weekend IS NOT NULL
    ORDER BY restaurant, scraped_at;
"""

# ─────────────────────────────────────────────
# WPI SUMMARY QUERY (SQL-level sanity check)
# ─────────────────────────────────────────────
WPI_SUMMARY_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        COUNT(CASE WHEN is_weekend = true  THEN 1 END)          AS weekend_records,
        COUNT(CASE WHEN is_weekend = false THEN 1 END)          AS weekday_records,
        ROUND(AVG(CASE WHEN is_weekend = true  THEN price END)::NUMERIC, 2) AS avg_price_weekend,
        ROUND(AVG(CASE WHEN is_weekend = false THEN price END)::NUMERIC, 2) AS avg_price_weekday,
        ROUND(
            (
                AVG(CASE WHEN is_weekend = true  THEN price END) -
                AVG(CASE WHEN is_weekend = false THEN price END)
            ) * 100.0 /
            NULLIF(AVG(CASE WHEN is_weekend = false THEN price END), 0)
        ::NUMERIC, 2)                                            AS wpi
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY restaurant, restaurant_category
    HAVING
        COUNT(CASE WHEN is_weekend = true  THEN 1 END) > 0
        AND COUNT(CASE WHEN is_weekend = false THEN 1 END) > 0
    ORDER BY wpi DESC NULLS LAST;
"""

# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────
def fetch_data():
    conn = get_connection()
    df   = pd.read_sql(QUERY, conn)
    conn.close()
    return df

def fetch_wpi_summary():
    conn = get_connection()
    df   = pd.read_sql(WPI_SUMMARY_QUERY, conn)
    conn.close()
    return df

# ─────────────────────────────────────────────
# MANN-WHITNEY U TEST
# One-tailed: tests if weekend prices > weekday prices
# ─────────────────────────────────────────────
def run_mann_whitney(weekend_prices, weekday_prices):
    if len(weekend_prices) < 2 or len(weekday_prices) < 2:
        return None, None, False

    stat, p_value = mannwhitneyu(
        weekend_prices,
        weekday_prices,
        alternative='greater'   # one-tailed: weekend > weekday
    )
    return stat, round(p_value, 4), p_value < 0.05

# ─────────────────────────────────────────────
# CORE ANALYSIS
# Per restaurant × category:
#   - Compute WPI
#   - Run Mann-Whitney U test
#   - Flag significant premiums
# ─────────────────────────────────────────────
def compute_wpi(df):
    results = []

    groups = df.groupby(['restaurant', 'restaurant_category'])

    for (restaurant, category), group in groups:
        weekend_prices = group[group['is_weekend'] == True]['price'].values
        weekday_prices = group[group['is_weekend'] == False]['price'].values

        if len(weekend_prices) == 0 or len(weekday_prices) == 0:
            continue

        avg_weekend = weekend_prices.mean()
        avg_weekday = weekday_prices.mean()

        if avg_weekday == 0:
            continue

        wpi = round((avg_weekend - avg_weekday) / avg_weekday * 100, 2)

        stat, p_value, significant = run_mann_whitney(weekend_prices, weekday_prices)

        results.append({
            'restaurant'        : restaurant,
            'category'          : category,
            'avg_price_weekend' : round(avg_weekend, 2),
            'avg_price_weekday' : round(avg_weekday, 2),
            'wpi'               : wpi,
            'weekend_records'   : len(weekend_prices),
            'weekday_records'   : len(weekday_prices),
            'mw_stat'           : stat,
            'p_value'           : p_value,
            'significant'       : significant,
            'verdict'           : (
                'Weekend premium confirmed' if significant and wpi > 0  else
                'Cheaper on weekends'       if significant and wpi < 0  else
                'No significant change'
            )
        })

    return pd.DataFrame(results).sort_values('wpi', ascending=False)

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df, path=None):
    if path is None:
        path = ROOT_DIR / 'outputs' / 'reports' / 'weekend_premium_results.csv'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q4 — Weekend Premium Analysis")
    print("=" * 60)

    # SQL-level sanity check
    print("\n[1] SQL-level WPI Summary:")
    summary = fetch_wpi_summary()

    if summary.empty:
        print("⚠️  No weekend data yet.")
        print("    Keep scheduler running through Saturday–Sunday.")
        print("    Run this again on Monday.")
        sys.exit()

    print(summary.to_string(index=False))

    # Full Python analysis with Mann-Whitney
    print("\n[2] Full Analysis with Statistical Test:")
    df = fetch_data()

    if df.empty:
        print("⚠️  No data found. Check v_analysis_base.")
        sys.exit()

    print(f"    Total records   : {len(df)}")
    print(f"    Weekend records : {df['is_weekend'].sum()}")
    print(f"    Weekday records : {(~df['is_weekend']).sum()}")

    results = compute_wpi(df)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results, 'analytics_weekend_premium', engine)

    if results.empty:
        print("⚠️  Not enough weekend/weekday data to compute WPI.")
    else:
        print("\n[3] WPI Results:")
        print(results.to_string(index=False))
        save_results(results)

    print("\n" + "=" * 60)