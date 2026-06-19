# Price Surge · Zomato Dynamic Pricing Intelligence

> *Do food delivery apps secretly change prices throughout the day? Does rain make your biryani more expensive? I built a system to find out.*

**TL;DR:** Automated end-to-end pipeline monitoring Zomato prices across 19 restaurants — 72K+ observations, 214 price change events, statistical proof that weather has zero effect on pricing, and one brand responsible for 78% of all dynamic pricing activity.

---

[![Landing Page](https://img.shields.io/badge/🌐%20Landing%20Page-Live-E23744?style=for-the-badge)](https://laren27.github.io/Price-Surge)
[![Live API](https://img.shields.io/badge/⚡%20Live%20API-Swagger%20UI-22c55e?style=for-the-badge)](https://price-surge.onrender.com/docs)
[![License](https://img.shields.io/badge/License-MIT-2D7DD2?style=for-the-badge)](LICENSE)

---

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Browser%20Automation-2D8CFF?style=flat-square&logo=playwright&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=flat-square&logo=postgresql&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?style=flat-square&logo=fastapi&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?style=flat-square&logo=powerbi&logoColor=black)
![Supabase](https://img.shields.io/badge/Supabase-Cloud%20DB-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=flat-square&logo=render&logoColor=black)
![Telegram](https://img.shields.io/badge/Telegram-Alerts-26A5E4?style=flat-square&logo=telegram&logoColor=white)
![OpenWeatherMap](https://img.shields.io/badge/OpenWeatherMap-Weather%20API-FF6B35?style=flat-square&logo=openweathermap&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-Statistical%20Tests-8CAAE6?style=flat-square&logo=scipy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-150458?style=flat-square&logo=pandas&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Hosted-181717?style=flat-square&logo=github&logoColor=white)

---

## The Question

Zomato is one of India's largest food delivery platforms. Anecdotally, users report seeing different prices for the same dish at different times of day — higher during lunch hours, during rain, on weekends. But is this actually happening systematically, or is it confirmation bias?

I wanted real data. So I built a system to collect it.

---

## What I Built

A fully automated data pipeline that monitors **19 restaurants on Zomato** across **7 time slots every day**, stores every price observation, joins it with live weather data, runs statistical analysis, serves the results through a REST API, and fires Telegram alerts when significant price events occur.

No manual work. No sampling. Just a scheduler that wakes up, scrapes, stores, and goes back to sleep — every single day.

```
Playwright Scraper → PostgreSQL → Analytics Engine → FastAPI → Power BI Dashboard
                                                             → Telegram Alerts
```

**The stack:** Python · Playwright · PostgreSQL · FastAPI · Power BI · Telegram Bot API · OpenWeatherMap · SciPy

---

## Key Findings

After collecting **72,000+ price observations** across 19 restaurants over several weeks:

| Finding | Result |
|---|---|
| Total valid price change events | **214** (after quality filters) |
| Most dynamic restaurant | **Faasos** — DPI score 54.1 |
| Market static rate | **73.7%** of restaurants show zero dynamic pricing |
| Weather effect on prices | **None** — 0/19 restaurants show significant rain or temperature effect (p > 0.05) |
| Weekend premium | **Restaurant-specific** — Wow! Momo shows 18.96% uplift; most show none |
| Faasos dominance | **167 of 214** price change events from a single brand |

**The short answer:** Dynamic pricing on Zomato exists, but it is highly concentrated in a single brand (Faasos) and has nothing to do with weather. The popular belief that rain makes food more expensive is not supported by the data.

---

## Architecture

### The Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│                         SCHEDULER                              │
│           Fixed slots: 10:00 12:00 14:00 16:00                 │
│                        18:00 20:00 22:00                       │
│           Exits at 23:00 · MIN_GAP = 60 minutes                │
└──────────────┬──────────────────┬──────────────────────────────┘
               │                  │
               ▼                  ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  PLAYWRIGHT      │  │  OPENWEATHERMAP  │
    │  SCRAPER         │  │  weather.py      │
    │                  │  │                  │
    │  iPhone 13 Pro   │  │  Temp, humidity, │
    │  emulation       │  │  rain condition  │
    │  Bhubaneswar geo │  │  per scrape slot │
    │  headless=False  │  │                  │
    └────────┬─────────┘  └────────┬─────────┘
             │                     │
             │                     |  scrape_session_id (shared env var)
             │                     │
             ▼                     ▼
    ┌─────────────────────────────────────────┐
    │              POSTGRESQL                 │
    │                                         │
    │  prices      — item-level observations  │
    │  weather     — per-session conditions   │
    │  restaurants — 19 monitored outlets     │
    │  analytics_* — 15 pre-computed tables   │
    └──────────────────┬──────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────┐
    │           ANALYTICS ENGINE              │
    │           run_all.py                    │
    │                                         │
    │  Atomic PL/pgSQL block via              │
    │  refresh_analytics.sql                  │
    │                                         │
    │  · Dynamic Pricing Index (DPI)          │
    │  · Rain Premium (RPI)                   │
    │  · Weekend Premium (WPI)                │
    │  · Stability Score                      │
    │  · Synchronized Pricing                 │
    │  · Hourly Patterns                      │
    │  · Category Sensitivity                 │
    │  · Temperature Effect                   │
    │  · Mann-Whitney U · Kruskal-Wallis      │
    └──────────────────┬──────────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
    ┌──────────────────┐  ┌──────────────────┐
    │    FASTAPI       │  │   TELEGRAM BOT   │
    │                  │  │                  │
    │  10 REST         │  │  5 alert types   │
    │  endpoints       │  │  A–E wired into  │
    │  Swagger UI      │  │  scheduler       │
    │  /docs           │  │                  │
    └────────┬─────────┘  └──────────────────┘
             │
             ▼
    ┌──────────────────┐
    │    POWER BI      │
    │                  │
    │  7-page          │
    │  interactive     │
    │  dashboard       │
    │  23 relationships│
    └──────────────────┘
```

### Why These Technical Choices

**`scrape_session_id` architecture** — The scraper and weather collector run as separate subprocesses. To join price and weather data precisely, I generate a single UUID before either subprocess launches and pass it via environment variable. Both processes write the same session ID to their respective tables, enabling exact joins without timestamp ambiguity. This was the most important architectural decision in the project.

**`headless=False` constraint** — Zomato's bot detection reliably blocks headless Chromium. The scraper runs with a visible browser window using iPhone 13 Pro viewport, Bhubaneswar geolocation (20.2961°N, 85.8245°E), and `--disable-http2`. Cookies are injected from `zomato_cookies.json` before navigation. This combination consistently bypasses detection.

**Redux SSR state extraction** — Zomato's menu data is not in the HTML. It lives in `window.__PRELOADED_STATE__`, a double-escaped JSON blob embedded in a `<script>` tag. Extraction requires parsing the Redux state, then decoding the double-escaped string via `.encode('utf-8').decode('unicode_escape')` before `json.loads()`.

**Pre-computed analytics, not DAX** — All statistical scores (Mann-Whitney U, Kruskal-Wallis, p-values, DPI weights) are computed in Python and stored in PostgreSQL. Power BI DAX only handles display logic. This keeps the dashboard fast, keeps the math auditable, and separates concerns cleanly.

**Atomic analytics refresh** — All 10 analytics scripts are orchestrated as a single atomic PL/pgSQL block in `refresh_analytics.sql`, executed via `run_all.py`. If any step fails, the entire refresh rolls back. No partial states, no stale analytics tables.

---

## Technical Challenges

**PostgreSQL corruption recovery** — Mid-project, a pgAdmin crash corrupted `pg_ctl.exe` and the pgAdmin Python environment. Full reinstall required. Data was recovered by exporting all tables to CSV via `COPY` commands from psql, reinstalling PostgreSQL cleanly, and re-importing from CSV. Lesson: `pg_dump` after every significant data collection run.

**Playwright network instability** — On a home connection, Playwright frequently throws `ERR_NETWORK_CHANGED` and `ERR_NAME_NOT_RESOLVED` mid-scrape. Solution: a retry wrapper with `MAX_RETRIES=3` and 60-second sleep between attempts, so a brief connection drop doesn't waste an entire scrape slot.

**Telegram SSL conflict** — PostgreSQL's Windows installer sets a `REQUESTS_CA_BUNDLE` environment variable that overrides the system certificate store, breaking `requests` SSL verification. Fix: `verify=False` + `urllib3.disable_warnings()` scoped to the Telegram alert module only.

**`TELEGRAM_CHAT_ID` type error** — Telegram's API returns chat IDs as integers but environment variables are always strings. The bot silently failed until `int(os.getenv("TELEGRAM_CHAT_ID"))` was added.

---

## Project Structure

```
Price-Surge/
│
├── index.html                  # Project landing page (GitHub Pages)
├── requirements.txt            # Python dependencies
├── .env                        # Local environment variables (not committed)
│
├── scheduler/
│   └── scheduler.py            # Main orchestrator — fixed clock slots, gap guard
│
├── src/
│   ├── scraping/
│   │   ├── zomato_scraper.py   # Playwright scraper — iPhone emulation, Redux extraction
│   │   ├── weather.py          # OpenWeatherMap collector
│   │   ├── database.py         # Scraping-layer DB connection
│   │   └── save_cookies.py     # One-time cookie capture utility
│   │
│   ├── analytics/
│   │   ├── run_all.py          # Analytics orchestrator
│   │   ├── refresh_analytics.sql # Atomic PL/pgSQL refresh block
│   │   ├── dynamic_pricing_index.py
│   │   ├── rain_premium.py
│   │   ├── weekend_premium.py
│   │   ├── stability_score.py
│   │   ├── synchronized_pricing.py
│   │   ├── hourly_patterns.py
│   │   ├── category_sensitivity.py
│   │   └── temperature_effect.py
│   │
│   ├── api/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── database.py         # RealDictCursor connection pool
│   │   ├── models.py           # Pydantic models with Optional types
│   │   └── routers/
│   │       ├── restaurants.py  # /restaurants, /latest-prices, /price-history
│   │       └── analysis.py     # /analysis/* endpoints
│   │
│   ├── alerts/
│   │   └── telegram.py         # 5 alert types wired to scheduler
│   │
│   └── utils/
│       └── db_writer.py        # Shared write utilities
│
└── data/
    ├── raw/
    │   ├── menu_prices.csv     # Raw price observations export
    │   └── weather_data.csv    # Raw weather data export
    └── processed/              # Analytics output folders
```

---

## API Reference

**Base URL:** `https://price-surge.onrender.com`  
**Interactive Docs:** `https://price-surge.onrender.com/docs`

> Note: The API runs on Render's free tier and may take 30–60 seconds to wake up on first request.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/restaurants` | List all 19 monitored restaurants |
| GET | `/latest-prices` | Most recent price snapshot, all restaurants |
| GET | `/price-history/{restaurant}` | Full price time series for one restaurant |
| GET | `/analysis/rain-premium` | Rain Price Index (RPI) per restaurant and category |
| GET | `/analysis/weekend-premium` | Weekend Price Index (WPI) per restaurant |
| GET | `/analysis/restaurant-rankings` | Full DPI leaderboard with scores |
| GET | `/analysis/category-analysis` | Price sensitivity scores by food category |
| GET | `/analysis/hourly-patterns` | Average price by hour across all restaurants |
| GET | `/analysis/price-correlation` | Synchronized pricing Pearson correlation matrix |

---

## Try It — Quick API Examples

> The API is live. No setup needed. First request may take 30–60s to wake up (free tier).

**Get the full DPI leaderboard:**
```bash
curl https://price-surge.onrender.com/analysis/restaurant-rankings
```
```json
[
  {
    "restaurant_name": "Faasos",
    "dpi_score": 54.1,
    "rpi_score": 0.12,
    "wpi_score": 0.08,
    "price_change_count": 167,
    "rank": 1
  },
  {
    "restaurant_name": "Wow! Momo",
    "dpi_score": 33.6,
    "rpi_score": 0.04,
    "wpi_score": 0.18,
    "price_change_count": 18,
    "rank": 2
  }
]
```

**Get hourly price patterns:**
```bash
curl https://price-surge.onrender.com/analysis/hourly-patterns
```
```json
[
  { "hour_of_day": 10, "avg_price_change_pct": 0.012 },
  { "hour_of_day": 12, "avg_price_change_pct": 0.031 },
  { "hour_of_day": 18, "avg_price_change_pct": 0.028 },
  { "hour_of_day": 22, "avg_price_change_pct": 0.009 }
]
```

**Get rain premium analysis:**
```bash
curl https://price-surge.onrender.com/analysis/rain-premium
```
```json
[
  {
    "restaurant_name": "Faasos",
    "rain_premium_pct": 1.2,
    "p_value": 0.43,
    "significant": false
  }
]
```

> Full interactive docs at [`/docs`](https://price-surge.onrender.com/docs) — try every endpoint in the browser.

---

## Dynamic Pricing Index (DPI)

The DPI is a composite score I designed to rank restaurants by how aggressively they practice dynamic pricing. It combines four signals:

```
DPI = (RPI × 0.20) + (WPI × 0.20) + (Temp × 0.10) + (PVS × 0.50)
```

| Component | Weight | What it measures |
|-----------|--------|------------------|
| RPI — Rain Price Index | 20% | Price uplift during rain vs clear weather |
| WPI — Weekend Price Index | 20% | Price uplift on weekends vs weekdays |
| Temp — Temperature Effect | 10% | Price correlation with temperature bands |
| PVS — Price Volatility Score | 50% | Count of price change events (normalized) |

PVS carries the highest weight because frequency of price changes is the strongest signal of intentional dynamic pricing behavior.

---

## Running Locally

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- A Zomato account with valid session cookies

### Setup

```bash
# Clone the repo
git clone https://github.com/Laren27/Price-Surge.git
cd Price-Surge

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env
# Fill in your DB credentials and API keys
```

### Environment Variables

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=zomato_prices
DB_USER=postgres
DB_PASSWORD=your_password
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
OPENWEATHER_API_KEY=your_api_key
```

### Run the scraper scheduler

```bash
python scheduler/scheduler.py
```

### Run the API

```bash
uvicorn src.api.main:app --reload
```

### Refresh analytics

```bash
python src/analytics/run_all.py
```

---

## Data Collection Methodology

- **Restaurants monitored:** 19 restaurants across Bhubaneswar on Zomato
- **Collection frequency:** 7 fixed slots daily — 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
- **Data per scrape:** All menu items with current prices per restaurant
- **Price change filter:** `price > ₹50`, `prev_price > ₹50`, `|diff| ≤ ₹50`, `|diff/prev| ≤ 30%`, gap ≤ 6 hours
- **Weather data:** Temperature, humidity, and rain condition captured per scrape session via OpenWeatherMap
- **Total observations:** 72,000+ rows in the `prices` table

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Laren Sahu** · Data Analyst  
Bhubaneswar, Odisha, India  
[LinkedIn](https://www.linkedin.com/in/laren-sahu-681177309) · [GitHub](https://github.com/Laren27)
