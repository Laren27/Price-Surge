# src/analytics/temperature_effect.py
#
# Q6 — Temperature Effect Analysis
# Question : Do menu prices change during extreme heat?
# Output   : Price response by temperature band + temp_effect_score per restaurant
# Method   : Kruskal-Wallis test across 3 bands (Cool/Normal/Hot)
# Formula  : temp_effect_score = (avg_hot - avg_normal) / avg_normal × 100
#
# Run from anywhere:
#   python src/analytics/temperature_effect.py

import pandas as pd
from scipy.stats import kruskal
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
QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        item_name,
        price,
        temperature,
        temperature_band,
        scraped_at
    FROM v_analysis_base
    WHERE price           IS NOT NULL
      AND temperature      IS NOT NULL
      AND temperature_band IS NOT NULL
    ORDER BY restaurant, scraped_at;
"""

BAND_SUMMARY_QUERY = """
    SELECT
        temperature_band,
        COUNT(*)                                AS total_records,
        ROUND(MIN(temperature)::NUMERIC, 1)     AS temp_min,
        ROUND(MAX(temperature)::NUMERIC, 1)     AS temp_max,
        ROUND(AVG(price)::NUMERIC, 2)           AS avg_price,
        ROUND(STDDEV(price)::NUMERIC, 2)        AS price_stddev
    FROM v_analysis_base
    WHERE price IS NOT NULL AND temperature IS NOT NULL
    GROUP BY temperature_band
    ORDER BY avg_price DESC;
"""

PER_RESTAURANT_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        temperature_band,
        COUNT(*)                                AS total_records,
        ROUND(AVG(price)::NUMERIC, 2)           AS avg_price
    FROM v_analysis_base
    WHERE price IS NOT NULL AND temperature IS NOT NULL
    GROUP BY restaurant, restaurant_category, temperature_band
    ORDER BY restaurant, temperature_band;
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
# KRUSKAL-WALLIS TEST
# Non-parametric — tests if any band differs
# Use when comparing 3+ groups
# p < 0.05 = at least one band is significantly different
# ─────────────────────────────────────────────
def run_kruskal(cool_prices, normal_prices, hot_prices):
    groups = [g for g in [cool_prices, normal_prices, hot_prices] if len(g) >= 2]
    if len(groups) < 2:
        return None, None, False
    stat, p_value = kruskal(*groups)
    return stat, round(p_value, 4), p_value < 0.05

# ─────────────────────────────────────────────
# CORE ANALYSIS
# Per restaurant × category:
#   - Compute avg price per band
#   - Compute temp_effect_score (Hot vs Normal)
#   - Run Kruskal-Wallis
# ─────────────────────────────────────────────
def compute_temp_effect(df):
    results = []

    groups = df.groupby(['restaurant', 'restaurant_category'])

    for (restaurant, category), group in groups:
        cool_prices   = group[group['temperature_band'] == 'Cool']['price'].values
        normal_prices = group[group['temperature_band'] == 'Normal']['price'].values
        hot_prices    = group[group['temperature_band'] == 'Hot']['price'].values

        avg_cool   = round(cool_prices.mean(), 2)   if len(cool_prices)   > 0 else None
        avg_normal = round(normal_prices.mean(), 2) if len(normal_prices) > 0 else None
        avg_hot    = round(hot_prices.mean(), 2)    if len(hot_prices)    > 0 else None

        # temp_effect_score: Hot vs Normal
        if avg_hot is not None and avg_normal is not None and avg_normal != 0:
            temp_effect_score = round((avg_hot - avg_normal) / avg_normal * 100, 2)
        else:
            temp_effect_score = None

        stat, p_value, significant = run_kruskal(cool_prices, normal_prices, hot_prices)

        # handle NaN p_value from zero-variance distributions (e.g. identical prices across bands)
        import math
        if p_value is None or (isinstance(p_value, float) and math.isnan(p_value)):
            p_value     = 1.0
            significant = False

        results.append({
            'restaurant'        : restaurant,
            'category'          : category,
            'avg_price_cool'    : avg_cool,
            'avg_price_normal'  : avg_normal,
            'avg_price_hot'     : avg_hot,
            'temp_effect_score' : temp_effect_score,
            'cool_records'      : len(cool_prices),
            'normal_records'    : len(normal_prices),
            'hot_records'       : len(hot_prices),
            'kw_stat'           : stat,
            'p_value'           : p_value,
            'significant'       : significant,
            'verdict'           : (
                'Price rises in heat'   if significant and temp_effect_score and temp_effect_score > 0 else
                'Price drops in heat'   if significant and temp_effect_score and temp_effect_score < 0 else
                'No significant change'
            )
        })

    return pd.DataFrame(results).sort_values('temp_effect_score', ascending=False, na_position='last')
# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df_results, df_band_summary, df_per_restaurant):
    out = ROOT_DIR / 'data' / 'processed' / 'temperature_effect'
    out.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(out / 'temperature_effect_results.csv', index=False)
    df_band_summary.to_csv(out / 'temperature_band_summary.csv', index=False)
    df_per_restaurant.to_csv(out / 'temperature_per_restaurant.csv', index=False)
    print(f"\n✅ Results saved to {out}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q6 — Temperature Effect Analysis")
    print("=" * 60)

    print("\n[1] Band Distribution:")
    df_band_summary = fetch(BAND_SUMMARY_QUERY)
    print(df_band_summary.to_string(index=False))

    print("\n[2] Fetching full data...")
    df              = fetch(QUERY)
    df_per_restaurant = fetch(PER_RESTAURANT_QUERY)

    if df.empty:
        print("⚠️  No data found.")
        sys.exit()

    print(f"    Total records   : {len(df)}")
    print(f"    Temp range      : {df['temperature'].min()}°C — {df['temperature'].max()}°C")
    print(f"    Bands present   : {df['temperature_band'].unique().tolist()}")

    print("\n[3] Running Analysis...")
    results = compute_temp_effect(df)
    print(results.to_string(index=False))

    save_results(results, df_band_summary, df_per_restaurant)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results,           'analytics_temperature_effect',             engine)
    save_df_to_db(df_band_summary,   'analytics_temperature_band',               engine)
    save_df_to_db(df_per_restaurant, 'analytics_temperature_per_restaurant',     engine)

    print("\n" + "=" * 60)