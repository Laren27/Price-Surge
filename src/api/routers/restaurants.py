# src/api/routers/restaurants.py

from fastapi import APIRouter, Query
from src.api.database import query

router = APIRouter(tags=["Restaurants"])


@router.get("/restaurants")
def get_restaurants():
    """List all 19 monitored restaurants with their primary category."""
    rows = query("""
        SELECT
            restaurant,
            category,
            COUNT(*) AS total_observations
        FROM analytics_dynamic_pricing_index
        RIGHT JOIN (
            SELECT DISTINCT restaurant FROM prices
        ) r USING (restaurant)
        GROUP BY restaurant, category
        ORDER BY restaurant ASC
    """)
    return {"count": len(rows), "data": rows}


@router.get("/latest-prices")
def get_latest_prices():
    """Most recent price snapshot across all restaurants."""
    rows = query("""
        SELECT DISTINCT ON (restaurant, item_name)
            restaurant,
            category,
            item_name,
            price,
            scraped_at
        FROM prices
        ORDER BY restaurant, item_name, scraped_at DESC
    """)
    return {
        "snapshot_description": "Most recent price per item per restaurant",
        "count": len(rows),
        "data": rows
    }


@router.get("/price-history/{restaurant}")
def get_price_history(
    restaurant: str,
    days: int = Query(default=7, ge=1, le=30, description="Number of days of history (1–30)")
):
    """
    Returns a clean daily price history snapshot for a specific restaurant.
    Reduces thousands of raw data logs into easy-to-read daily trends.
    """
    rows = query("""
        SELECT
            item_name,
            category,
            DATE(scraped_at) AS history_date,
            ROUND(AVG(price)::numeric, 2) AS avg_price,
            MIN(price) AS min_price,
            MAX(price) AS max_price,
            COUNT(*) AS observations_that_day
        FROM prices
        WHERE restaurant = %s
          AND scraped_at >= (SELECT MAX(scraped_at) FROM prices) - INTERVAL '1 day' * %s
        GROUP BY item_name, category, DATE(scraped_at)
        ORDER BY history_date DESC, item_name ASC
    """, (restaurant, days))

    return {
        "restaurant": restaurant,
        "days_requested": days,
        "total_tracked_items_days": len(rows),
        "data": rows
    }