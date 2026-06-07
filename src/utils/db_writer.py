# src/utils/db_writer.py
#
# Shared utility for writing analytics DataFrames to PostgreSQL.
# Used by all analytics files to persist results as DB tables.
# Also fixes the pandas UserWarning about psycopg2 by using SQLAlchemy.
#
# Usage in any analytics file:
#   from src.utils.db_writer import get_engine, save_df_to_db
#   engine = get_engine()
#   save_df_to_db(df, 'analytics_rain_premium', engine)

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# ─────────────────────────────────────────────
# ENGINE
# SQLAlchemy engine — reuse across calls
# ─────────────────────────────────────────────
from urllib.parse import quote_plus

def get_engine():
    password = quote_plus(os.getenv("POSTGRES_PASSWORD"))
    return create_engine(
        f"postgresql+psycopg2://postgres:{password}@localhost:5432/zomato_prices"
    )
# ─────────────────────────────────────────────
# SAVE DATAFRAME TO DB
# if_exists='replace' — overwrites table each run
# index=False        — don't write pandas index
# ─────────────────────────────────────────────
def save_df_to_db(df, table_name, engine):
    """
    Writes a DataFrame to PostgreSQL as a table.
    Replaces the table completely on each run — same
    behavior as the CSV overwrite pattern.
    """
    try:
        df.to_sql(
            name      = table_name,
            con       = engine,
            if_exists = 'replace',
            index     = False
        )
        print(f"✅ DB  → {table_name} ({len(df)} rows)")
    except Exception as e:
        print(f"❌ DB write failed for {table_name}: {e}")