# src/analytics/synchronized_pricing.py
#
# Q8 — Synchronized Pricing Analysis
# Question : Do restaurants raise prices simultaneously,
#            suggesting market-wide coordination?
# Output   : Correlation matrix of price change vectors
#            High correlation = coordinated behavior
# Method   : LAG price deltas per session, then correlate
#            across restaurants at same timestamps
#
# Run from anywhere:
#   python src/analytics/synchronized_pricing.py

import pandas as pd
import numpy as np
from pathlib import Path
import psycopg2
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine, save_df_to_db
# ─────────────────────────────────────────────
# QUERY
# Pull avg segment price per restaurant per session
# This is the unit for delta calculation —
# item-level is too noisy for correlation
# ─────────────────────────────────────────────
QUERY = """
    SELECT
        restaurant,
        restaurant_category,
        scrape_session_id,
        scraped_at,
        is_rainy,
        ROUND(AVG(price)::NUMERIC, 2)   AS avg_segment_price
    FROM v_analysis_base
    WHERE price IS NOT NULL
    GROUP BY
        restaurant,
        restaurant_category,
        scrape_session_id,
        scraped_at,
        is_rainy
    ORDER BY restaurant, scraped_at;
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
# COMPUTE PRICE DELTAS
# For each restaurant+category, compute
# session-over-session price change
# ─────────────────────────────────────────────
def compute_deltas(df):
    df = df.sort_values(['restaurant', 'restaurant_category', 'scraped_at'])
    df['prev_price'] = df.groupby(['restaurant', 'restaurant_category'])['avg_segment_price'].shift(1)
    df['price_delta'] = df['avg_segment_price'] - df['prev_price']
    df = df.dropna(subset=['price_delta'])
    return df

# ─────────────────────────────────────────────
# BUILD CORRELATION MATRIX
# Pivot: rows = scrape_session, cols = restaurant+category
# Then correlate columns
# ─────────────────────────────────────────────
def build_correlation_matrix(df_deltas, rain_only=False):
    if rain_only:
        df_deltas = df_deltas[df_deltas['is_rainy'] == True]
        if len(df_deltas) < 3:
            return None, "Not enough rainy sessions for correlation"

    # Create unique label per restaurant+category
    df_deltas = df_deltas.copy()
    df_deltas['label'] = df_deltas['restaurant'] + ' (' + df_deltas['restaurant_category'] + ')'

    pivot = df_deltas.pivot_table(
        index='scraped_at',
        columns='label',
        values='price_delta',
        aggfunc='mean'
    )

    # Drop columns with too many NaN (restaurants with sparse data)
    pivot = pivot.dropna(thresh=int(len(pivot) * 0.5), axis=1)

    if pivot.shape[1] < 2:
        return None, "Not enough restaurants with sufficient session overlap"

    corr_matrix = pivot.corr(method='pearson')
    return corr_matrix, None

# ─────────────────────────────────────────────
# FIND HIGHLY CORRELATED PAIRS
# Extract pairs with correlation > threshold
# ─────────────────────────────────────────────
def find_correlated_pairs(corr_matrix, threshold=0.6):
    pairs = []
    cols  = corr_matrix.columns

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) >= threshold:
                pairs.append({
                    'restaurant_a' : cols[i],
                    'restaurant_b' : cols[j],
                    'correlation'  : round(corr_val, 4),
                    'strength'     : (
                        'Very Strong' if abs(corr_val) >= 0.8 else
                        'Strong'      if abs(corr_val) >= 0.6 else
                        'Moderate'
                    )
                })

    return pd.DataFrame(pairs).sort_values('correlation', ascending=False)

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(corr_matrix, corr_matrix_rain, df_pairs, df_pairs_rain):
    out = ROOT_DIR / 'data' / 'processed' / 'synchronized_pricing'
    out.mkdir(parents=True, exist_ok=True)

    if corr_matrix is not None:
        corr_matrix.to_csv(out / 'sync_correlation_matrix_all.csv')
    if corr_matrix_rain is not None:
        corr_matrix_rain.to_csv(out / 'sync_correlation_matrix_rain.csv')
    if not df_pairs.empty:
        df_pairs.to_csv(out / 'sync_correlated_pairs_all.csv', index=False)
    if not df_pairs_rain.empty:
        df_pairs_rain.to_csv(out / 'sync_correlated_pairs_rain.csv', index=False)

    print(f"\n✅ Results saved to {out}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q8 — Synchronized Pricing Analysis")
    print("=" * 60)

    print("\n[1] Fetching session-level data...")
    df = fetch(QUERY)

    if df.empty:
        print("⚠️  No data found.")
        sys.exit()

    print(f"    Restaurants     : {df['restaurant'].nunique()}")
    print(f"    Sessions        : {df['scrape_session_id'].nunique()}")
    print(f"    Rainy sessions  : {df[df['is_rainy'] == True]['scrape_session_id'].nunique()}")

    print("\n[2] Computing price deltas...")
    df_deltas = compute_deltas(df)
    print(f"    Delta rows      : {len(df_deltas)}")

    # ── All sessions ──
    print("\n[3] Correlation Matrix — All Sessions:")
    corr_matrix, err = build_correlation_matrix(df_deltas, rain_only=False)
    if err:
        print(f"⚠️  {err}")
        corr_matrix = None
    else:
        print(corr_matrix.round(3).to_string())
        df_pairs = find_correlated_pairs(corr_matrix, threshold=0.6)
        print(f"\n── Highly Correlated Pairs (r ≥ 0.6) ──")
        print(df_pairs.to_string(index=False) if not df_pairs.empty else "None found above threshold")

    # ── Rain sessions only ──
    print("\n[4] Correlation Matrix — Rain Sessions Only:")
    corr_matrix_rain, err_rain = build_correlation_matrix(df_deltas, rain_only=True)
    if err_rain:
        print(f"⚠️  {err_rain}")
        corr_matrix_rain = None
        df_pairs_rain    = pd.DataFrame()
    else:
        print(corr_matrix_rain.round(3).to_string())
        df_pairs_rain = find_correlated_pairs(corr_matrix_rain, threshold=0.6)
        print(f"\n── Highly Correlated Pairs During Rain (r ≥ 0.6) ──")
        print(df_pairs_rain.to_string(index=False) if not df_pairs_rain.empty else "None found above threshold")

    df_pairs      = df_pairs      if corr_matrix      is not None else pd.DataFrame()
    df_pairs_rain = df_pairs_rain if corr_matrix_rain is not None else pd.DataFrame()

    save_results(corr_matrix, corr_matrix_rain, df_pairs, df_pairs_rain)
    # ── Save to DB ──
    engine = get_engine()
    if corr_matrix is not None:
        save_df_to_db(corr_matrix.reset_index(),      'analytics_sync_correlation_all',  engine)
    if corr_matrix_rain is not None:
        save_df_to_db(corr_matrix_rain.reset_index(), 'analytics_sync_correlation_rain', engine)
    if not df_pairs.empty:
        save_df_to_db(df_pairs,                       'analytics_sync_pairs_all',        engine)
    if not df_pairs_rain.empty:
        save_df_to_db(df_pairs_rain,                  'analytics_sync_pairs_rain',       engine)

    print("\n" + "=" * 60)