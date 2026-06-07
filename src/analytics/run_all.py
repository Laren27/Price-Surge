#python src\analytics\run_all.py# src/analytics/run_all.py
#
# Runs all analytics scripts in dependency order.
# Never stops on error — logs failures and continues.
# DPI always runs last since it depends on all others.
#
# Run from anywhere:
#   python src/analytics/run_all.py

import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR  = Path(__file__).resolve().parent.parent.parent
ANALYTICS = ROOT_DIR / 'src' / 'analytics'

# ─────────────────────────────────────────────
# RUN ORDER
# DPI is always last — depends on all others
# ─────────────────────────────────────────────
SCRIPTS = [
    ('  Rain Premium',         ANALYTICS / 'rain_premium.py'),
    ('  Weekend Premium',      ANALYTICS / 'weekend_premium.py'),
    ('  Temperature Effect',   ANALYTICS / 'temperature_effect.py'),
    ('  Stability Score',      ANALYTICS / 'stability_score.py'),
    ('  Synchronized Pricing', ANALYTICS / 'synchronized_pricing.py'),
    ('  Category Sensitivity', ANALYTICS / 'category_sensitivity.py'),
    ('  Dynamic Pricing Index',ANALYTICS / 'dynamic_pricing_index.py'),
    ('  Hourly Patterns',      ANALYTICS / 'hourly_patterns.py'),
]

# ─────────────────────────────────────────────
# RUNNER
# capture_output=False → prints live to terminal
# Never raises — logs result and moves on
# ─────────────────────────────────────────────
def run_script(label, path):
    print(f"\n{'─' * 60}")
    print(f"▶  {label}")
    print(f"{'─' * 60}")

    if not path.exists():
        print(f"⚠️  File not found: {path} — skipping")
        return 'skipped'

    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=False,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ {label} — done")
            return 'success'
        else:
            print(f"❌ {label} — failed with code {result.returncode}")
            return 'failed'

    except Exception as e:
        print(f"❌ {label} — exception: {e}")
        return 'failed'

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Analytics Runner — All Scripts")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    summary = {}

    for label, path in SCRIPTS:
        status = run_script(label, path)
        summary[label] = status

    # ── Final Summary ──
    print(f"\n{'=' * 60}")
    print(f"  Finished : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─' * 60}")
    for label, status in summary.items():
        icon = '✅' if status == 'success' else '❌' if status == 'failed' else '⏭️'
        print(f"  {icon}  {label} — {status}")
    print("=" * 60)