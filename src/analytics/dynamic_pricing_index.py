# src/analytics/dynamic_pricing_index.py
import pandas as pd
import numpy as np
from pathlib import Path
import psycopg2
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG
from src.utils.db_writer import get_engine

OUT_DIR = ROOT_DIR / 'data' / 'processed' / 'dynamic_pricing_index'

DPI_QUERY = """
    SELECT
        r.restaurant,
        r.category,
        r.rpi,
        w.wpi,
        t.temp_effect_score AS temp_effect,
        s.pvs_normalized
    FROM analytics_rain_premium r
    JOIN analytics_weekend_premium w
        ON r.restaurant = w.restaurant AND r.category = w.category
    JOIN analytics_temperature_effect t
        ON r.restaurant = t.restaurant AND r.category = t.category
    JOIN analytics_stability_score s
        ON r.restaurant = s.restaurant AND r.category = s.restaurant_category;
"""

def fetch_data():
    conn = psycopg2.connect(**DB_CONFIG)
    df   = pd.read_sql(DPI_QUERY, conn)
    conn.close()
    return df

def normalize_series(series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return series * 0
    return (series - min_val) / (max_val - min_val) * 100

if __name__ == "__main__":
    print("=" * 60)
    print("Q2 — Clean Dynamic Pricing Index Calculation")
    print("=" * 60)

    base = fetch_data()

    weights = {'rpi': 0.30, 'wpi': 0.20, 'temp': 0.10, 'pvs': 0.50}

    base['rpi_norm']        = normalize_series(base['rpi'])
    base['wpi_norm']        = normalize_series(base['wpi'])
    base['temp_effect_norm']= normalize_series(base['temp_effect'])

    base['dpi'] = (
        base['rpi_norm']         * weights['rpi']  +
        base['wpi_norm']         * weights['wpi']  +
        base['temp_effect_norm'] * weights['temp'] +
        base['pvs_normalized']   * weights['pvs']
    ).round(2)

    base['dpi_rank'] = base['dpi'].rank(ascending=False, method='min').astype(int)
    base['pricing_behavior'] = pd.cut(
        base['dpi'],
        bins=[-np.inf, 25, 50, 75, np.inf],
        labels=['Static Pricer', 'Low Dynamic', 'Moderate Dynamic', 'Aggressive Dynamic']
    )

    results = base.drop(columns=['rpi_norm', 'wpi_norm', 'temp_effect_norm'])
    results = results.sort_values('dpi', ascending=False)

    print("\n── DPI Leaderboard ──")
    print(results[['restaurant', 'category', 'dpi', 'dpi_rank', 'pricing_behavior']].to_string(index=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / 'dynamic_pricing_index_results.csv', index=False)

    engine = get_engine()
    results.to_sql(
        'analytics_dynamic_pricing_index',
        con=engine,
        if_exists='replace',
        index=False
    )
    print("✅ Successfully updated analytics_dynamic_pricing_index table.")
    print("=" * 60)