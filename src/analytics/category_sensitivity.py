# src/analytics/category_sensitivity.py
#
# Q5 — Category Sensitivity Analysis
# Question : Which food categories experience the largest price increases
#            during adverse conditions?
# Output   : Category Sensitivity Score — ranking of categories by surge magnitude
# Method   : Apply RPI (rain) and WPI (weekend) calculations per dish_type
#
# Run from anywhere:
#   python src/analytics/category_sensitivity.py

import pandas as pd
from scipy.stats import mannwhitneyu
from pathlib import Path
import psycopg2
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine, save_df_to_db
# ─────────────────────────────────────────────
# QUERY
# ─────────────────────────────────────────────
QUERY = """
    SELECT
        dish_type,
        restaurant_category,
        price,
        is_rainy,
        is_weekend,
        temperature_band,
        scraped_at
    FROM v_analysis_base
    WHERE price    IS NOT NULL
      AND dish_type != 'Other'
    ORDER BY dish_type, scraped_at;
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
# MANN-WHITNEY
# ─────────────────────────────────────────────
def run_mann_whitney(group_a, group_b):
    if len(group_a) < 2 or len(group_b) < 2:
        return None, None, False
    stat, p_value = mannwhitneyu(group_a, group_b, alternative='greater')
    return stat, round(p_value, 4), p_value < 0.05

# ─────────────────────────────────────────────
# CORE ANALYSIS
# Per dish_type:
#   - RPI  (rain premium)
#   - WPI  (weekend premium)
#   - Temp sensitivity (hot vs normal)
#   - Category Sensitivity Score = avg of available indices
# ─────────────────────────────────────────────
def compute_category_sensitivity(df):
    results = []

    for dish_type, group in df.groupby('dish_type'):

        # ── RPI ──
        rainy_prices = group[group['is_rainy'] == True]['price'].values
        clear_prices = group[group['is_rainy'] == False]['price'].values

        if len(rainy_prices) > 0 and len(clear_prices) > 0 and clear_prices.mean() != 0:
            rpi = round((rainy_prices.mean() - clear_prices.mean()) / clear_prices.mean() * 100, 2)
            _, rpi_p, rpi_sig = run_mann_whitney(rainy_prices, clear_prices)
        else:
            rpi, rpi_p, rpi_sig = None, None, False

        # ── WPI ──
        weekend_prices = group[group['is_weekend'] == True]['price'].values
        weekday_prices = group[group['is_weekend'] == False]['price'].values

        if len(weekend_prices) > 0 and len(weekday_prices) > 0 and weekday_prices.mean() != 0:
            wpi = round((weekend_prices.mean() - weekday_prices.mean()) / weekday_prices.mean() * 100, 2)
            _, wpi_p, wpi_sig = run_mann_whitney(weekend_prices, weekday_prices)
        else:
            wpi, wpi_p, wpi_sig = None, None, False

        # ── Temp sensitivity ──
        hot_prices    = group[group['temperature_band'] == 'Hot']['price'].values
        normal_prices = group[group['temperature_band'] == 'Normal']['price'].values

        if len(hot_prices) > 0 and len(normal_prices) > 0 and normal_prices.mean() != 0:
            temp_effect = round((hot_prices.mean() - normal_prices.mean()) / normal_prices.mean() * 100, 2)
        else:
            temp_effect = None

        # ── Category Sensitivity Score ──
        # Average of whichever indices are available
        available = [v for v in [rpi, wpi, temp_effect] if v is not None]
        sensitivity_score = round(sum(available) / len(available), 2) if available else None

        results.append({
            'dish_type'          : dish_type,
            'total_records'      : len(group),
            'rpi'                : rpi,
            'rpi_p_value'        : rpi_p,
            'rpi_significant'    : rpi_sig,
            'wpi'                : wpi,
            'wpi_p_value'        : wpi_p,
            'wpi_significant'    : wpi_sig,
            'temp_effect'        : temp_effect,
            'sensitivity_score'  : sensitivity_score,
            'rainy_records'      : len(rainy_prices),
            'weekend_records'    : len(weekend_prices),
            'hot_records'        : len(hot_prices),
        })

    df_results = (
        pd.DataFrame(results)
        .sort_values('sensitivity_score', ascending=False, na_position='last')
    )
    return df_results

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df):
    out  = ROOT_DIR / 'data' / 'processed' / 'category_sensitivity'
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'category_sensitivity_results.csv'
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q5 — Category Sensitivity Analysis")
    print("=" * 60)

    print("\n[1] Fetching data...")
    df = fetch(QUERY)

    if df.empty:
        print("⚠️  No data found.")
        sys.exit()

    print(f"    Total records   : {len(df)}")
    print(f"    Dish types      : {df['dish_type'].unique().tolist()}")
    print(f"    Rainy records   : {df['is_rainy'].sum()}")
    print(f"    Weekend records : {df['is_weekend'].sum()}")

    print("\n[2] Computing Category Sensitivity Scores...")
    results = compute_category_sensitivity(df)

    print("\n── Category Sensitivity Ranking ──")
    print(results.to_string(index=False))

    save_results(results)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results, 'analytics_category_sensitivity', engine)

    print("\n" + "=" * 60)