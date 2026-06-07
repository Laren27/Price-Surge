# src/analytics/rain_premium.py
#
# Q1 — Rain Premium Analysis
# Question : Do restaurants increase menu prices during rainfall?
# Output   : Rain Premium Index (RPI) per restaurant per category
# Formula  : RPI = (avg_price_rain - avg_price_clear) / avg_price_clear × 100
# Test     : Mann-Whitney U (one-tailed) — p < 0.05 = significant surge
#
# Run from project root:
#   python src/analytics/rain_premium.py

import pandas as pd
from scipy.stats import mannwhitneyu
import psycopg2
import sys
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine, save_df_to_db

# ─────────────────────────────────────────────
# QUERY
# Pull every price row with its rain flag
# Filter out rows where weather data is missing
# ─────────────────────────────────────────────
QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        dish_type,
        item_name,
        price,
        is_rainy,
        weather_condition,
        scraped_at
    FROM v_analysis_base
    WHERE is_rainy IS NOT NULL
      AND price     IS NOT NULL
    ORDER BY restaurant, scraped_at;
"""

# ─────────────────────────────────────────────
# RPI QUERY (SQL-level)
# Quick summary — useful for sanity check
# before running the full Python analysis
# ─────────────────────────────────────────────
RPI_SUMMARY_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        COUNT(CASE WHEN is_rainy = true  THEN 1 END)        AS rainy_records,
        COUNT(CASE WHEN is_rainy = false THEN 1 END)        AS clear_records,
        ROUND(AVG(CASE WHEN is_rainy = true  THEN price END)::NUMERIC, 2) AS avg_price_rain,
        ROUND(AVG(CASE WHEN is_rainy = false THEN price END)::NUMERIC, 2) AS avg_price_clear,
        ROUND(
            (
                AVG(CASE WHEN is_rainy = true  THEN price END) -
                AVG(CASE WHEN is_rainy = false THEN price END)
            ) * 100.0 /
            NULLIF(AVG(CASE WHEN is_rainy = false THEN price END), 0)
        ::NUMERIC, 2)                                        AS rpi
    FROM v_analysis_base
    WHERE is_rainy IS NOT NULL
      AND price IS NOT NULL
    GROUP BY restaurant, restaurant_category
    HAVING
        COUNT(CASE WHEN is_rainy = true  THEN 1 END) > 0
        AND COUNT(CASE WHEN is_rainy = false THEN 1 END) > 0
    ORDER BY rpi DESC NULLS LAST;
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


def fetch_rpi_summary():
    conn = get_connection()
    df   = pd.read_sql(RPI_SUMMARY_QUERY, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────
# MANN-WHITNEY U TEST
# One-tailed: tests if rainy prices > clear prices
# Returns: stat, p_value, significant (bool)
#
# Why Mann-Whitney and not t-test?
# Price data is not guaranteed to be normally
# distributed — Mann-Whitney is non-parametric
# and works on any distribution.
# ─────────────────────────────────────────────
def run_mann_whitney(rainy_prices, clear_prices):
    if len(rainy_prices) < 2 or len(clear_prices) < 2:
        return None, None, False

    stat, p_value = mannwhitneyu(
        rainy_prices,
        clear_prices,
        alternative='greater'   # one-tailed: rain > clear
    )
    return stat, round(p_value, 4), p_value < 0.05


# ─────────────────────────────────────────────
# CORE ANALYSIS
# Per restaurant × category:
#   - Compute RPI
#   - Run Mann-Whitney U test
#   - Flag significant surgers
# ─────────────────────────────────────────────
def compute_rpi(df):
    results = []

    groups = df.groupby(['restaurant', 'restaurant_category'])

    for (restaurant, category), group in groups:
        rainy_prices = group[group['is_rainy'] == True]['price'].values
        clear_prices = group[group['is_rainy'] == False]['price'].values

        # Skip if either condition has no data
        if len(rainy_prices) == 0 or len(clear_prices) == 0:
            continue

        avg_rain  = rainy_prices.mean()
        avg_clear = clear_prices.mean()

        if avg_clear == 0:
            continue

        rpi = round((avg_rain - avg_clear) / avg_clear * 100, 2)

        stat, p_value, significant = run_mann_whitney(rainy_prices, clear_prices)

        results.append({
            'restaurant'         : restaurant,
            'category'           : category,
            'avg_price_rain'     : round(avg_rain, 2),
            'avg_price_clear'    : round(avg_clear, 2),
            'rpi'                : rpi,
            'rainy_records'      : len(rainy_prices),
            'clear_records'      : len(clear_prices),
            'mw_stat'            : stat,
            'p_value'            : p_value,
            'significant'        : significant,
            'verdict'            : (
                'Surge confirmed'    if significant and rpi > 0  else
                'Drop during rain'   if significant and rpi < 0  else
                'No significant change'
            )
        })

    return pd.DataFrame(results).sort_values('rpi', ascending=False)


# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df, path='Price Surge/data/processed/rain_premium_results/rain_premium_results.csv'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q1 — Rain Premium Analysis")
    print("=" * 60)

    # SQL-level sanity check first
    print("\n[1] SQL-level RPI Summary:")
    summary = fetch_rpi_summary()
    print(summary.to_string(index=False))

    # Full Python analysis with Mann-Whitney
    print("\n[2] Full Analysis with Statistical Test:")
    df      = fetch_data()

    if df.empty:
        print("⚠️  No data found. Check v_analysis_base.")
        sys.exit()

    print(f"    Total records   : {len(df)}")
    print(f"    Rainy records   : {df['is_rainy'].sum()}")
    print(f"    Clear records   : {(~df['is_rainy']).sum()}")

    results = compute_rpi(df)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results, 'analytics_rain_premium', engine)

    if results.empty:
        print("⚠️  Not enough rainy/clear data yet to compute RPI.")
        print("    Keep collecting — need at least one rainy session.")
    else:
        print("\n[3] RPI Results:")
        print(results.to_string(index=False))
        save_results(results)

    print("\n" + "=" * 60)