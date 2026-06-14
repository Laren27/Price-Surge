# src/analytics/synchronized_pricing.py
# NOTE: Pearson correlation analysis requires item-level hourly pivots that are
# computationally intensive in pure SQL. This script is a REFERENCE PLACEHOLDER.
# The production path (refresh_analytics.sql) creates empty tables for these outputs.
# Full correlation logic to be implemented in a future iteration.
import pandas as pd
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'synchronized_pricing'

def fetch_price_pivot():
    """
    Fetches hourly price changes per restaurant as a pivot for correlation analysis.
    Returns wide-format DataFrame: rows = hours, columns = restaurants.
    """
    query = """
        SELECT
            hour_of_day,
            restaurant,
            COALESCE(ROUND(AVG(pct_change)::NUMERIC, 4), 0.0) AS avg_pct_change
        FROM v_price_changes
        GROUP BY hour_of_day, restaurant
        ORDER BY hour_of_day, restaurant;
    """
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(query, conn)
    conn.close()
    return df.pivot(index='hour_of_day', columns='restaurant', values='avg_pct_change').fillna(0)

def compute_correlation_pairs(pivot_df, min_correlation=0.7):
    corr_matrix = pivot_df.corr()
    pairs = []
    restaurants = corr_matrix.columns.tolist()
    for i in range(len(restaurants)):
        for j in range(i + 1, len(restaurants)):
            r = corr_matrix.iloc[i, j]
            if abs(r) >= min_correlation:
                strength = 'Strong' if abs(r) >= 0.85 else 'Moderate'
                pairs.append({
                    'restaurant_a': restaurants[i],
                    'restaurant_b': restaurants[j],
                    'correlation':  round(r, 4),
                    'strength':     strength
                })
    return pd.DataFrame(pairs) if pairs else pd.DataFrame(
        columns=['restaurant_a', 'restaurant_b', 'correlation', 'strength']
    )

if __name__ == "__main__":
    print("=" * 60)
    print("Q8 — Synchronized Pricing Correlation Analysis")
    print("=" * 60)

    print("\n[1] Building hourly price pivot matrix...")
    pivot = fetch_price_pivot()

    print("[2] Computing correlation pairs (threshold: r >= 0.70)...")
    sync_all  = compute_correlation_pairs(pivot, min_correlation=0.70)
    sync_rain = compute_correlation_pairs(pivot, min_correlation=0.80)

    print(f"\n── Correlated Pairs (All) : {len(sync_all)} pairs ──")
    if not sync_all.empty:
        print(sync_all.to_string(index=False))
    else:
        print("  No significant correlation pairs found.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sync_all.to_csv(OUT_DIR / 'sync_correlated_pairs_all.csv',  index=False)
    sync_rain.to_csv(OUT_DIR / 'sync_correlated_pairs_rain.csv', index=False)

    print("\n[3] Syncing to database tables...")
    engine = get_engine()
    sync_all.to_sql('analytics_sync_pairs_all',  con=engine, if_exists='replace', index=False)
    sync_rain.to_sql('analytics_sync_pairs_rain', con=engine, if_exists='replace', index=False)

    print("✅ Successfully updated analytics_sync_pairs_all and analytics_sync_pairs_rain.")
    print("=" * 60)