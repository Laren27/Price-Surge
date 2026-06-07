# src/analytics/stability_score.py
#
# Q7 — Pricing Stability Analysis
# Question : Which restaurants maintain the most stable pricing over time?
# Output   : Pricing Volatility Score (PVS) — normalized 0 to 100
# Basis    : price_change_events (actual temporal price changes)
#            CV retained for reference but NOT used for PVS
# Note     : CV = σ/μ measures menu price diversity, not dynamic pricing.
#            price_change_events is the correct signal for temporal volatility.
#
# Run from anywhere:
#   python src/analytics/stability_score.py

import pandas as pd
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
        scraped_at,
        hour_of_day
    FROM v_analysis_base
    WHERE price IS NOT NULL
    ORDER BY restaurant, item_name, scraped_at;
"""

CV_SUMMARY_QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        COUNT(*)                                                          AS total_records,
        ROUND(AVG(price)::NUMERIC, 2)                                     AS avg_price,
        ROUND(STDDEV(price)::NUMERIC, 2)                                  AS price_stddev,
        ROUND((STDDEV(price) / NULLIF(AVG(price), 0) * 100)::NUMERIC, 4) AS cv_pct
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY restaurant, restaurant_category
    ORDER BY cv_pct DESC;
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
# NORMALIZE 0–100
# ─────────────────────────────────────────────
def normalize(series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return series * 0
    return (series - min_val) / (max_val - min_val) * 100

# ─────────────────────────────────────────────
# COUNT PRICE CHANGE EVENTS
# Per restaurant × category:
# counts how many times an item's price
# actually changed between scrape sessions
# ─────────────────────────────────────────────
def count_price_changes(df):
    change_counts = []

    for (restaurant, category), group in df.groupby(['restaurant', 'restaurant_category']):
        total_changes = 0
        for item, item_group in group.groupby('item_name'):
            item_group    = item_group.sort_values('scraped_at')
            changes       = (item_group['price'] != item_group['price'].shift()).sum() - 1
            total_changes += max(changes, 0)

        change_counts.append({
            'restaurant'          : restaurant,
            'restaurant_category' : category,
            'price_change_events' : total_changes
        })

    return pd.DataFrame(change_counts)

# ─────────────────────────────────────────────
# CORE ANALYSIS
# ─────────────────────────────────────────────
def compute_stability(df, df_cv_summary):

    # ── Count actual price change events ──
    df_changes = count_price_changes(df)

    # ── Merge CV + change events ──
    results = df_cv_summary.merge(df_changes, on=['restaurant', 'restaurant_category'], how='left')

    # ── PVS based on price_change_events (not CV) ──
    results['pvs_normalized'] = normalize(results['price_change_events']).round(2)

    # ── CV normalized separately — for reference only ──
    results['cv_normalized']  = normalize(results['cv_pct']).round(2)

    # ── Stability label based on pvs_normalized ──
    results['stability_label'] = pd.cut(
        results['pvs_normalized'],
        bins=[0, 25, 50, 75, 100],
        labels=['Very Stable', 'Stable', 'Volatile', 'Very Volatile'],
        include_lowest=True
    )

    return results.sort_values('pvs_normalized', ascending=False)

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df):
    out  = ROOT_DIR / 'data' / 'processed' / 'stability_score'
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'stability_score_results.csv'
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q7 — Pricing Stability Analysis")
    print("=" * 60)

    print("\n[1] SQL-level CV Summary (reference only):")
    df_cv_summary = fetch(CV_SUMMARY_QUERY)
    print(df_cv_summary.to_string(index=False))

    print("\n[2] Fetching full time series...")
    df = fetch(QUERY)

    if df.empty:
        print("⚠️  No data found.")
        sys.exit()

    print(f"    Total records   : {len(df)}")
    print(f"    Restaurants     : {df['restaurant'].nunique()}")
    print(f"    Scrape sessions : {df['scraped_at'].nunique()}")

    print("\n[3] Computing PVS from price change events...")
    results = compute_stability(df, df_cv_summary)

    print("\n── Volatility Leaderboard (100 = most volatile) ──")
    print(results[[
        'restaurant', 'restaurant_category', 'avg_price',
        'price_change_events', 'pvs_normalized',
        'cv_pct', 'cv_normalized', 'stability_label'
    ]].to_string(index=False))

    save_results(results)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results, 'analytics_stability_score', engine)

    print("\n" + "=" * 60)