# Price Surge · Zomato Dynamic Pricing Intelligence

**Role:** Solo developer & data engineer — built the scraper, analytics pipeline, REST API, and dashboard end-to-end.

> *Do food delivery apps secretly change prices throughout the day? Does rain make your biryani more expensive? I built a system to find out.*

**TL;DR:** Automated end-to-end pipeline monitoring Zomato prices across 19 restaurants — 1.4M+ price observations, Mann-Whitney U and Kruskal-Wallis tests confirming weather has zero effect on pricing (p > 0.05 across all 19 restaurants), dynamic pricing concentrated in just 5 of 19 restaurants, and zero evidence of coordinated pricing across the market.

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

![Dashboard screenshot](path/to/dashboard-screenshot.png)
*Replace this path with a screenshot or GIF of the Power BI dashboard or a sample API response.*

---

## Table of Contents

- [The Question](#the-question)
- [What I Built](#what-i-built)
- [Key Findings](#key-findings)
- [What This Project Does Not Claim](#what-this-project-does-not-claim)
- [Statistical Methodology](#statistical-methodology)
- [Architecture](#architecture)
- [Technical Challenges](#technical-challenges)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Try It — Quick API Examples](#try-it--quick-api-examples)
- [Dynamic Pricing Index (DPI)](#dynamic-pricing-index-dpi)
- [Running Locally](#running-locally)
- [Data Collection Methodology](#data-collection-methodology)

---

## How to Evaluate Quickly

If you're reviewing this repo and want the fastest path to understanding it, open files in this order:

1. **`src/scraping/zomato_scraper.py`** — the scraper and Redux state extraction logic (the most non-obvious part of the project)
2. **`src/analytics/run_all.py`** + **`src/analytics/refresh_analytics.sql`** — the analytics orchestration and atomic PL/pgSQL refresh engine
3. **`src/api/main.py`** + **`src/api/routers/analysis.py`** — the FastAPI endpoints serving the computed analytics
4. **`scheduler/scheduler.py`** — the 5-iteration scheduler logic (fixed slots, gap guard, retry wrapper)

Or skip the code entirely and just hit the [live API](https://price-surge.onrender.com/docs) — every endpoint is interactive via Swagger UI.

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

After collecting **1.4M+ price observations** across 19 restaurants over several weeks:

| Finding | Result |
|---|---|
| Dynamic pricing concentration | **5 of 19** restaurants account for all price change events |
| Market static rate | **73.7%** of restaurants show zero dynamic pricing |
| Weather effect on prices | **None** — 0/19 restaurants show significant rain or temperature effect (p > 0.05) |
| Weekend premium | **Restaurant-specific** — one restaurant shows 18.96% uplift; most show none |
| Synchronized pricing pairs | **0** — no restaurants move prices in coordination |
| Leading brand dominance | One brand accounts for the **majority of all price change events** |

> DPI scores and event counts are live-computed from the database. Current leaderboard available at [`/analysis/restaurant-rankings`](https://price-surge.onrender.com/analysis/restaurant-rankings).

**The short answer:** Dynamic pricing on Zomato exists, but it is concentrated in a small cluster of brands and has nothing to do with weather. The popular belief that rain makes food more expensive is not supported by the data.

---

## What This Project Does Not Claim

The dataset contains menu prices and weather readings only — no order data, no session data, no demand signals.

| Incorrect Claim | Why It Cannot Be Made |
|---|---|
| "Rain increases biryani demand" | No order data collected |
| "Customers prefer momos during bad weather" | No customer behaviour data |
| "Restaurant X loses revenue when it surges" | No revenue data available |
| "Conversion rates drop during price spikes" | No session or click data |

Every finding in this project is a **pricing observation**, not a demand conclusion.

---

## Statistical Methodology

Statistical tests were selected to match the data's non-normal distribution. No normality assumption was made.

| Test | Applied To | Why |
|---|---|---|
| **Mann-Whitney U** | Price distributions: rain vs. no-rain per restaurant | Non-parametric comparison of two independent groups |
| **Kruskal-Wallis** | Price distributions across three temperature bands (Cool / Normal / Hot) | Non-parametric comparison of three or more groups |
| **Pearson correlation** | Synchronized pricing detection across restaurant pairs | Computed in-memory via pandas; threshold \|r\| ≥ 0.4, min_periods=3 |

**Significance threshold:** p < 0.05. Zero of 19 restaurants cleared this bar for any weather variable — confirming the null hypothesis that weather does not drive pricing on this platform.

---

## Architecture

### The Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         SCHEDULER                               │
│           Fixed slots: 10:00 12:00 14:00 16:00                 │
│                        18:00 20:00 22:00                        │
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
             │   scrape_session_id (shared env var)
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
    │  8-page          │
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

**Atomic analytics refresh** — All analytics computations are orchestrated as a single atomic PL/pgSQL block in `refresh_analytics.sql`, executed via `run_all.py`. Writes to `analytics_*_staging` tables first, then drops live tables and renames staging in a single transaction. If any step fails, the entire refresh rolls back. No partial states, no stale analytics tables mid-refresh.

**Z-score normalization over Min-Max** — Initial implementation used Min-Max normalization. One restaurant acting as a hyper-aggressive outlier pulled the ceiling upward, compressing the remaining 80% of competitors into a narrow band near zero and masking genuine pricing signals. Refactored to centered Z-score normalization (Z × 15 + 50) with hard clamps at [0, 100] to preserve relative spread across the market regardless of outlier behavior.

**PVS as dominant DPI anchor (50% weight)** — In a market where 73.7% of restaurants are completely static, standard normalization maps their shared zero variance to an artificial score of ~38.2 rather than absolute zero. Elevating Price Volatility Score (actual frequency of price change events) to dominant weight converts weather-based indexes into secondary tiebreakers and eliminates this noise floor artifact.

**Scheduler design — 5 iterations** — The scheduler went through five design versions before reaching production stability: relative timer → fixed clock slots → minimum gap guard → operating window with intraday startup rules → network retry wrapper. Each iteration solved a specific real-world failure mode (clock drift, double-scraping, mid-day startup gaps, transient network drops).

---

## Technical Challenges

**PostgreSQL corruption recovery** — Mid-project, a pgAdmin crash corrupted `pg_ctl.exe` and the pgAdmin Python environment. Full reinstall required. Data was recovered by exporting all tables to CSV via `COPY` commands from psql, reinstalling PostgreSQL cleanly, and re-importing from CSV. Lesson: `pg_dump` after every significant data collection run.

**Playwright network instability** — On a home connection, Playwright frequently throws `ERR_NETWORK_CHANGED` and `ERR_NAME_NOT_RESOLVED` mid-scrape. Solution: a retry wrapper with `MAX_RETRIES=3` and 60-second sleep between attempts, so a brief connection drop doesn't waste an entire scrape slot.

**Playwright channel override** — Setting `channel='chrome'` silently ignored device emulation, reverting to desktop layout and breaking the mobile parser entirely. Fix: removed the channel flag and locked to Playwright's bundled Chromium binaries. Mobile device emulation and system Chrome channel flags are mutually exclusive.

**Min-Max normalization failure** — Initial DPI scoring compressed 14 static restaurants into a narrow non-zero band due to a single outlier, making completely static brands appear to have low-but-present dynamic behavior. Rebuilt the normalization layer using centered Z-score with distribution scaling, which correctly separates active pricers from static ones.

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
│   └── scheduler.py            # Main orchestrator — fixed clock slots, gap guard, retry wrapper
│
├── src/
│   ├── scraping/
│   │   ├── zomato_scraper.py   # Playwright scraper — iPhone emulation, Redux state extraction
│   │   ├── weather.py          # OpenWeatherMap collector
│   │   ├── database.py         # Scraping-layer DB connection
│   │   └── save_cookies.py     # One-time cookie capture utility (run before first scrape)
│   │
│   ├── analytics/
│   │   ├── run_all.py          # Analytics orchestrator — single psycopg2 session + Pearson
│   │   ├── refresh_analytics.sql  # Active pipeline — atomic PL/pgSQL DO $$ block (15 tables)
│   │   ├── dynamic_pricing_index.py   # DEPRECATED — reference only, not part of active pipeline
│   │   ├── rain_premium.py            # DEPRECATED — reference only
│   │   ├── weekend_premium.py         # DEPRECATED — reference only
│   │   ├── stability_score.py         # DEPRECATED — reference only
│   │   ├── synchronized_pricing.py    # DEPRECATED — reference only
│   │   ├── hourly_patterns.py         # DEPRECATED — reference only
│   │   ├── category_sensitivity.py    # DEPRECATED — reference only
│   │   └── temperature_effect.py      # DEPRECATED — reference only
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

> **Active pipeline files:** `scheduler.py` → `zomato_scraper.py` + `weather.py` → `run_all.py` → `refresh_analytics.sql`. The individual `.py` scripts in `analytics/` are kept as reference only and are not executed.

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
| GET | `/analysis/restaurant-rankings` | Full DPI leaderboard with live scores |
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

**Get hourly price patterns:**
```bash
curl https://price-surge.onrender.com/analysis/hourly-patterns
```

**Get rain premium analysis:**
```bash
curl https://price-surge.onrender.com/analysis/rain-premium
```

> Full interactive docs at [`/docs`](https://price-surge.onrender.com/docs) — try every endpoint in the browser.

---

## Dynamic Pricing Index (DPI)

The DPI is a composite score designed to rank restaurants by how aggressively they practice dynamic pricing. It combines four signals weighted by their analytical reliability:

```
DPI = (PVS × 0.50) + (RPI × 0.20) + (WPI × 0.20) + (Temp × 0.10)
```

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| PVS — Price Volatility Score | 50% | Frequency of genuine price change events (normalized) |
| RPI — Rain Price Index | 20% | Price uplift during rain vs. clear weather |
| WPI — Weekend Price Index | 20% | Price uplift on weekends vs. weekdays |
| Temp — Temperature Effect | 10% | Price correlation with temperature bands |

**Why PVS carries the highest weight:** In a market where 73.7% of restaurants show zero price changes, standard normalization artifacts cluster all static players at a non-zero score (~38.2) rather than zero. Anchoring on raw change event frequency correctly separates active pricers from static ones, with weather indexes acting as tiebreakers for restaurants that do show movement.

**Normalization:** Each component is Z-score normalized (Z × 15 + 50) before weighting, then hard-clamped to [0, 100]. This prevents a single outlier from compressing the rest of the market into a narrow band — a failure mode observed with Min-Max normalization during development.

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
```

### Capture Zomato Session Cookies (one-time setup)

```bash
python src/scraping/save_cookies.py
```

A visible browser window will open. Log in to your Zomato account manually, wait for the homepage to load, then close the window. This saves your session tokens to `zomato_cookies.json`. Without this step, the scraper will run but return all prices as 0 — Zomato hides real menu prices from unauthenticated sessions.

> `zomato_cookies.json` is listed in `.gitignore` and will never be committed.

### Environment Variables

```bash
cp .env.example .env
# Fill in your DB credentials and API keys
```

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
- **Observations defined:** Each scrape captures prices for ~100+ menu items across 19 restaurants. 72K+ rows in the `prices` table × item-level granularity = 1.4M+ individual price data points tracked over the collection period.
- **Price change filter:** `price > ₹50`, `prev_price > ₹50`, `|diff| ≤ ₹50`, `|diff/prev| ≤ 30%`, gap ≤ 6 hours
- **Weather data:** Temperature, humidity, and rain condition captured per scrape session via OpenWeatherMap
- **Session linking:** Scraper and weather collector share a UUID (`scrape_session_id`) generated before each run, enabling exact price-weather joins without timestamp ambiguity
- **Normalization basis:** PVS normalized on `price_change_events` count, not coefficient of variation — corrects for restaurants with high CV but low actual change frequency

---

## Roadmap / Future Improvements

- Docker Compose setup (Postgres + API + seeded sample data) for one-command local evaluation
- Smoke tests for API endpoints and analytics runner
- CONTRIBUTING.md with developer quickstart

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Laren Sahu** · Data Analyst  
Bhubaneswar, Odisha, India  
[LinkedIn](https://www.linkedin.com/in/laren-sahu-681177309) · [GitHub](https://github.com/Laren27)
