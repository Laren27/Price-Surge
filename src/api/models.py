# src/api/models.py

from pydantic import BaseModel
from typing import Optional

# ── /restaurants ──────────────────────────────────────────────
class RestaurantItem(BaseModel):
    restaurant: str

class RestaurantsResponse(BaseModel):
    count: int
    data: list[RestaurantItem]

# ── /analysis/restaurant-rankings ────────────────────────────
class DPIEntry(BaseModel):
    restaurant: str
    category: Optional[str] = None
    rpi: Optional[float] = None
    wpi: Optional[float] = None
    temp_effect: Optional[float] = None
    pvs_normalized: Optional[float] = None
    dpi: Optional[float] = None
    dpi_rank: Optional[int] = None
    pricing_behavior: Optional[str] = None

class DPIResponse(BaseModel):
    metric: str = "Dynamic Pricing Index"
    weights: dict = {"RPI": 0.20, "WPI": 0.20, "Temp": 0.10, "PVS": 0.50}
    observation_period: str = "30 days"
    data: list[DPIEntry]

# ── /analysis/rain-premium ────────────────────────────────────
class RainPremiumEntry(BaseModel):
    restaurant: str
    category: Optional[str] = None
    rainy_records: Optional[int] = None
    clear_records: Optional[int] = None
    avg_change_rain: Optional[float] = None
    avg_change_clear: Optional[float] = None
    rpi: Optional[float] = None
    significant: Optional[bool] = None
    verdict: Optional[str] = None

class RainPremiumResponse(BaseModel):
    metric: str = "Rain Premium Index"
    unit: str = "percentage"
    observation_period: str = "30 days"
    data: list[RainPremiumEntry]

# ── /analysis/weekend-premium ────────────────────────────────
class WeekendPremiumEntry(BaseModel):
    restaurant: str
    category: Optional[str] = None
    weekend_records: Optional[int] = None
    weekday_records: Optional[int] = None
    avg_change_weekend: Optional[float] = None
    avg_change_weekday: Optional[float] = None
    wpi: Optional[float] = None
    significant: Optional[bool] = None
    verdict: Optional[str] = None

class WeekendPremiumResponse(BaseModel):
    metric: str = "Weekend Premium Index"
    unit: str = "percentage"
    observation_period: str = "30 days"
    data: list[WeekendPremiumEntry]

# ── /analysis/category-analysis ──────────────────────────────
class CategoryEntry(BaseModel):
    dish_type: Optional[str] = None
    total_change_events: Optional[int] = None
    rpi: Optional[float] = None
    wpi: Optional[float] = None
    sensitivity_score: Optional[float] = None

class CategoryResponse(BaseModel):
    metric: str = "Category Sensitivity"
    observation_period: str = "30 days"
    data: list[CategoryEntry]

# ── /analysis/hourly-patterns ────────────────────────────────
class HourlyEntry(BaseModel):
    hour_of_day: int
    total_change_events: Optional[int] = None
    avg_price_change_pct: Optional[float] = None

class HourlyResponse(BaseModel):
    metric: str = "Hourly Pricing Patterns"
    observation_period: str = "30 days"
    data: list[HourlyEntry]

# ── /analysis/price-correlation ──────────────────────────────
class WeatherCorrelationEntry(BaseModel):
    weather_condition: str
    avg_price: Optional[float] = None
    observation_count: Optional[int] = None

class WeatherCorrelationResponse(BaseModel):
    metric: str = "Market Weather Price Correlation"
    observation_period: str = "30 days"
    data: list[WeatherCorrelationEntry]