# src/analytics/dynamic_pricing_index.py
#
# Q2 — Dynamic Pricing Index (DPI)
# Question : Which restaurants are the most aggressive dynamic pricers overall?
# Output   : DPI leaderboard — single score per restaurant per category
# Formula  : DPI = (RPI × 0.35) + (WPI × 0.25) + (Temp_Effect × 0.15) + (PVS × 0.25)
# Note     : All inputs normalized to 0–100 before weights applied
#
# DEPENDS ON (run these first via run_all.py):
#   rain_premium.py       → data/processed/rain_premium_results/rain_premium_results.csv
#   weekend_premium.py    → data/processed/weekend_premium_results/weekend_premium_results.csv
#   temperature_effect.py → data/processed/temperature_effect/temperature_effect_results.csv
#   stability_score.py    → data/processed/stability_score/stability_score_results.csv
#
# Run from anywhere:
#   python src/analytics/dynamic_pricing_index.py

import pandas as pd
import numpy as np
from pathlib import Path
import sys
ROOT_DIR    = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))
from src.utils.db_writer import get_engine, save_df_to_db
PROCESSED   = ROOT_DIR / 'data' / 'processed'
OUT_DIR     = PROCESSED / 'dynamic_pricing_index'

# ─────────────────────────────────────────────
# WEIGHTS
# ─────────────────────────────────────────────
WEIGHTS = {
    'rpi'               : 0.35,
    'wpi'               : 0.25,
    'temp_effect_score' : 0.15,
    'pvs_normalized'    : 0.25,
}

# ─────────────────────────────────────────────
# LOAD RESULT FILES
# ─────────────────────────────────────────────
def load_results():
    files = {
        'rain'     : PROCESSED / 'rain_premium_results'   / 'rain_premium_results.csv',
        'weekend'  : PROCESSED / 'weekend_premium_results'/ 'weekend_premium_results.csv',
        'temp'     : PROCESSED / 'temperature_effect'     / 'temperature_effect_results.csv',
        'stability': PROCESSED / 'stability_score'        / 'stability_score_results.csv',
    }

    dfs = {}
    for key, path in files.items():
        if path.exists():
            dfs[key] = pd.read_csv(path)
            print(f"    ✅ Loaded {path.name}")
        else:
            dfs[key] = None
            print(f"    ⚠️  Missing {path.name} — filling with 0")

    return dfs

# ─────────────────────────────────────────────
# NORMALIZE 0–100
# ─────────────────────────────────────────────
def normalize_series(series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return series * 0
    return (series - min_val) / (max_val - min_val) * 100

# ─────────────────────────────────────────────
# BUILD DPI
# ─────────────────────────────────────────────
def compute_dpi(dfs):

    if dfs['rain'] is None:
        print("❌ rain_premium_results.csv is required. Run rain_premium.py first.")
        sys.exit()

    base = dfs['rain'][['restaurant', 'category', 'rpi']].copy()

    # ── Merge WPI ──
    if dfs['weekend'] is not None:
        wpi_df = dfs['weekend'][['restaurant', 'category', 'wpi']]
        base   = base.merge(wpi_df, on=['restaurant', 'category'], how='left')
    else:
        base['wpi'] = 0.0

    # ── Merge Temp Effect ──
    if dfs['temp'] is not None:
        temp_df = dfs['temp'][['restaurant', 'category', 'temp_effect_score']]
        base    = base.merge(temp_df, on=['restaurant', 'category'], how='left')
    else:
        base['temp_effect_score'] = 0.0

    # ── Merge PVS ──
    if dfs['stability'] is not None:
        pvs_df = dfs['stability'][['restaurant', 'restaurant_category', 'pvs_normalized']]
        pvs_df = pvs_df.rename(columns={'restaurant_category': 'category'})
        base   = base.merge(pvs_df, on=['restaurant', 'category'], how='left')
    else:
        base['pvs_normalized'] = 0.0

    # ── Fill NaN with 0 ──
    for col in ['rpi', 'wpi', 'temp_effect_score', 'pvs_normalized']:
        base[col] = base[col].fillna(0)

    # ── Normalize all inputs to 0–100 before applying weights ──
    base['rpi_norm']               = normalize_series(base['rpi'])
    base['wpi_norm']               = normalize_series(base['wpi'])
    base['temp_effect_score_norm'] = normalize_series(base['temp_effect_score'])
    # pvs_normalized already 0–100

    # ── Compute DPI ──
    base['dpi'] = (
        base['rpi_norm']               * WEIGHTS['rpi']               +
        base['wpi_norm']               * WEIGHTS['wpi']               +
        base['temp_effect_score_norm'] * WEIGHTS['temp_effect_score'] +
        base['pvs_normalized']         * WEIGHTS['pvs_normalized']
    ).round(2)

    # ── Rank ──
    base['dpi_rank'] = base['dpi'].rank(ascending=False, method='min').astype(int)

    # ── Label ──
    base['pricing_behavior'] = pd.cut(
        base['dpi'],
        bins=[-np.inf, 25, 50, 75, np.inf],
        labels=['Static Pricer', 'Low Dynamic', 'Moderate Dynamic', 'Aggressive Dynamic']
    )

    return base.sort_values('dpi', ascending=False)

# ─────────────────────────────────────────────
# SAVE OUTPUT
# ─────────────────────────────────────────────
def save_results(df):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / 'dynamic_pricing_index_results.csv'
    df.to_csv(path, index=False)
    print(f"\n✅ DPI results saved to {path}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Q2 — Dynamic Pricing Index")
    print("=" * 60)

    print("\n[1] Loading component results...")
    dfs = load_results()

    print("\n[2] Computing DPI...")
    results = compute_dpi(dfs)

    print("\n── DPI Leaderboard ──")
    print(results[[
        'dpi_rank', 'restaurant', 'category',
        'rpi_norm', 'wpi_norm', 'temp_effect_score_norm', 'pvs_normalized',
        'dpi', 'pricing_behavior'
    ]].to_string(index=False))

    print(f"\n── Weights Applied ──")
    for k, v in WEIGHTS.items():
        print(f"    {k:<20} : {v}")

    save_results(results)
    # ── Save to DB ──
    engine = get_engine()
    save_df_to_db(results, 'analytics_dynamic_pricing_index', engine)

    print("\n" + "=" * 60)