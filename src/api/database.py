# src/api/database.py

import psycopg2
import psycopg2.extras   # needed for RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv() # loads into os cache to retrieve with os.getenv("DB_HOST") etc. below

def get_connection():
    """
    Opens and returns a fresh PostgreSQL connection.
    Called at the start of every request, closed at the end.
    We don't keep a permanent connection open because
    connections can time out if left idle.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "zomato_prices"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )


def query(sql: str, params=None) -> list[dict]:
    """
    Runs a SELECT query and returns results as a list of dicts.
    
    RealDictCursor is the key here — normally psycopg2 returns
    tuples like (1, "Faasos", 54.1). RealDictCursor returns
    {"rank": 1, "restaurant": "Faasos", "dpi": 54.1} instead.
    FastAPI can serialize dicts to JSON automatically.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            results = cur.fetchall()
            return [dict(row) for row in results]  # convert from RealDictRow to plain dict
    finally:
        conn.close()  # always close, even if query fails