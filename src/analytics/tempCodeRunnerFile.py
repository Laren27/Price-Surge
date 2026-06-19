# src/analytics/run_all.py
import psycopg2
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraping.database import DB_CONFIG

SQL_SCRIPT_PATH = ROOT_DIR / 'src' / 'analytics' / 'refresh_analytics.sql'
PROCESSED_DIR   = ROOT_DIR / 'data' / 'processed'

LOCAL_CSV_EXPORTS = {
    'analytics_category_sensitivity':   'category_sensitivity/category_sensitivity_results.csv',
    'analytics_dynamic_pricing_index':  'dynamic_pricing_index/dynamic_pricing_index_results.csv',
    'analytics_hourly_overall':         'hourly_patterns/hourly_overall.csv',
    'analytics_hourly_per_restaurant':  'hourly_patterns/hourly_per_restaurant.csv',
    'analytics_hourly_peak_restaurant': 'hourly_patterns/hourly_peak_per_restaurant.csv',
    'analytics_peak_offpeak':           'hourly_patterns/peak_offpeak.csv',
    'analytics_rain_premium':           'rain_premium_results/rain_premium_results.csv',
    'analytics_stability_score':        'stability_score/stability_score_results.csv',
    'analytics_temperature_effect':     'temperature_effect/temperature_effect_results.csv',
    'analytics_weekend_premium':        'weekend_premium_results/weekend_premium_results.csv',
}

def compute_synchronized_pricing(conn):
    print("[3] Computing synchronized pricing pairs via Python math engine...")

    query = """
        SELECT restaurant, item_name, hour_of_day, is_rainy, pct_change
        FROM v_price_changes
        WHERE pct_change IS NOT NULL;
    """
    df = pd.read_sql(query, conn)

    if df.empty or len(df['restaurant'].unique()) < 2:
        print("    ⚠️  Not enough price change data to compute correlations. Creating empty placeholders.")
        empty_df = pd.DataFrame(columns=['restaurant_a', 'restaurant_b', 'correlation', 'strength'])
        return empty_df, empty_df.copy()

    pivot_all  = df.pivot_table(
        index=['item_name', 'hour_of_day'],
        columns='restaurant',
        values='pct_change',
        aggfunc='mean'
    )
    pivot_rain = df[df['is_rainy'] == True].pivot_table(
        index=['item_name', 'hour_of_day'],
        columns='restaurant',
        values='pct_change',
        aggfunc='mean'
    )

    def calculate_pairs(pivot_df):
        if pivot_df.shape[1] < 2:
            return pd.DataFrame(columns=['restaurant_a', 'restaurant_b', 'correlation', 'strength'])

        corr_matrix = pivot_df.corr(method='pearson', min_periods=3)
        pairs = []

        restaurants = corr_matrix.columns
        for i in range(len(restaurants)):
            for j in range(i + 1, len(restaurants)):
                val = corr_matrix.iloc[i, j]
                if not np.isnan(val) and abs(val) >= 0.4:
                    strength = 'Strong' if abs(val) >= 0.7 else 'Moderate'
                    pairs.append({
                        'restaurant_a': restaurants[i],
                        'restaurant_b': restaurants[j],
                        'correlation':  round(float(val), 4),
                        'strength':     strength
                    })

        if not pairs:
            return pd.DataFrame(columns=['restaurant_a', 'restaurant_b', 'correlation', 'strength'])

        return pd.DataFrame(pairs).sort_values(by='correlation', ascending=False)

    df_all  = calculate_pairs(pivot_all)
    df_rain = calculate_pairs(pivot_rain)

    return df_all, df_rain


def execute_pipeline():
    print("=" * 70)
    print("  Bulletproof Analytics Engine — Integrated Processing Unit")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if not SQL_SCRIPT_PATH.exists():
        print(f"❌ Critical Error: SQL file missing at {SQL_SCRIPT_PATH}")
        sys.exit(1)

    conn = None
    try:
        print("\n[1] Connecting to database cluster...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        print("[2] Executing atomic table calculation and swap blocks...")
        with open(SQL_SCRIPT_PATH, 'r') as f:
            cursor.execute(f.read())
        print("    ✅ Native database tables refreshed successfully.")

        # Compute correlations in-memory
        sync_all_df, sync_rain_df = compute_synchronized_pricing(conn)

        print("[4] Executing atomic staging write and swap for synchronized pairs...")
        from src.utils.db_writer import get_engine
        engine = get_engine()
        
        # Write to transient staging environments
        sync_all_df.to_sql('analytics_sync_pairs_all_staging', con=engine, if_exists='replace', index=False)
        sync_rain_df.to_sql('analytics_sync_pairs_rain_staging', con=engine, if_exists='replace', index=False)
        
        # Temporarily disable autocommit so DROP + RENAME are one atomic transaction
        conn.autocommit = False
        try:
            with conn.cursor() as swap_cursor:
                swap_cursor.execute("DROP TABLE IF EXISTS analytics_sync_pairs_all CASCADE;")
                swap_cursor.execute("ALTER TABLE analytics_sync_pairs_all_staging RENAME TO analytics_sync_pairs_all;")
                swap_cursor.execute("DROP TABLE IF EXISTS analytics_sync_pairs_rain CASCADE;")
                swap_cursor.execute("ALTER TABLE analytics_sync_pairs_rain_staging RENAME TO analytics_sync_pairs_rain;")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = True
        print("    ✅ Synchronized pricing tables swapped with zero-halt switchover.")

        print("\n[5] Generating clean local CSV snapshots...")
        for table, relative_path in LOCAL_CSV_EXPORTS.items():
            destination_file = PROCESSED_DIR / relative_path
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            pd.read_sql(f"SELECT * FROM {table};", conn).to_csv(destination_file, index=False)
            print(f"    -> Exported: data/processed/{relative_path}")

        sync_all_file  = PROCESSED_DIR / 'synchronized_pricing/sync_correlated_pairs_all.csv'
        sync_rain_file = PROCESSED_DIR / 'synchronized_pricing/sync_correlated_pairs_rain.csv'
        sync_all_file.parent.mkdir(parents=True, exist_ok=True)
        
        sync_all_df.to_csv(sync_all_file,  index=False)
        sync_rain_df.to_csv(sync_rain_file, index=False)
        print(f"    -> Exported: data/processed/synchronized_pricing/sync_correlated_pairs_all.csv  ({len(sync_all_df)} pairs)")
        print(f"    -> Exported: data/processed/synchronized_pricing/sync_correlated_pairs_rain.csv ({len(sync_rain_df)} pairs)")

        print("\n✅ Total Pipeline Run Successful! All 12 visualization matrices synchronized.")

    except Exception as e:
        print(f"\n❌ Execution Exception: Pipeline processing interrupted: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    execute_pipeline()