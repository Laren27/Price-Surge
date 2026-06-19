# src/api/routers/analysis.py

from fastapi import APIRouter
from src.api.database import query
from src.api.models import (
    DPIResponse, DPIEntry,
    RainPremiumResponse, RainPremiumEntry,
    WeekendPremiumResponse, WeekendPremiumEntry,
    CategoryResponse, CategoryEntry,
    HourlyResponse, HourlyEntry,
    WeatherCorrelationResponse, WeatherCorrelationEntry,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/restaurant-rankings", response_model=DPIResponse)
def get_restaurant_rankings():
    """Full DPI leaderboard — all restaurants ranked by Dynamic Pricing Index."""
    rows = query("""
        SELECT
            restaurant, category, rpi, wpi,
            temp_effect, pvs_normalized, dpi,
            dpi_rank, pricing_behavior
        FROM analytics_dynamic_pricing_index
        ORDER BY dpi_rank ASC
    """)
    return DPIResponse(data=[DPIEntry(**row) for row in rows])


@router.get("/rain-premium", response_model=RainPremiumResponse)
def get_rain_premium():
    """Rain Premium Index for all restaurants and categories."""
    rows = query("""
        SELECT
            restaurant, category, rainy_records, clear_records,
            avg_change_rain, avg_change_clear, rpi, significant, verdict
        FROM analytics_rain_premium
        ORDER BY rpi DESC
    """)
    return RainPremiumResponse(data=[RainPremiumEntry(**row) for row in rows])


@router.get("/weekend-premium", response_model=WeekendPremiumResponse)
def get_weekend_premium():
    """Weekend Premium Index for all restaurants and categories."""
    rows = query("""
        SELECT
            restaurant, category, weekend_records, weekday_records,
            avg_change_weekend, avg_change_weekday, wpi, significant, verdict
        FROM analytics_weekend_premium
        ORDER BY wpi DESC
    """)
    return WeekendPremiumResponse(data=[WeekendPremiumEntry(**row) for row in rows])


@router.get("/category-analysis", response_model=CategoryResponse)
def get_category_analysis():
    """Sensitivity scores by food category."""
    rows = query("""
        SELECT
            dish_type, total_change_events, rpi, wpi, sensitivity_score
        FROM analytics_category_sensitivity
        ORDER BY sensitivity_score DESC
    """)
    return CategoryResponse(data=[CategoryEntry(**row) for row in rows])


@router.get("/hourly-patterns", response_model=HourlyResponse)
def get_hourly_patterns():
    """Average price change activity by hour across all restaurants."""
    rows = query("""
        SELECT
            hour_of_day, total_change_events, avg_price_change_pct
        FROM analytics_hourly_overall
        ORDER BY hour_of_day ASC
    """)
    return HourlyResponse(data=[HourlyEntry(**row) for row in rows])


@router.get("/price-correlation", response_model=WeatherCorrelationResponse)
def get_price_correlation():
    """Average price by weather condition — market-wide correlation."""
    rows = query("""
        SELECT
            weather_condition, avg_price, observation_count
        FROM analytics_market_weather_price
        ORDER BY avg_price DESC
    """)
    return WeatherCorrelationResponse(data=[WeatherCorrelationEntry(**row) for row in rows])