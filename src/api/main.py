from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import restaurants, analysis

# ─────────────────────────────────────────────
#  TAG METADATA
#  Each tag maps to a router group and renders
#  as a collapsible section inside /docs
# ─────────────────────────────────────────────
tags_metadata = [
    {
        "name": "restaurants",
        "description": (
            "Retrieve raw restaurant listings, price observations, and item-level data. "
            "All prices are scraped live from Zomato across 19 restaurants in Bhubaneswar "
            "at 7 fixed time slots per day."
        ),
    },
    {
        "name": "analysis",
        "description": (
            "Statistical analytics computed from the scraped dataset. Includes the Dynamic "
            "Pricing Index (DPI), weather correlation results, weekend premium scores, "
            "price change events, and market-level summaries. All scores are pre-computed "
            "upstream — these endpoints serve read-only analytics results."
        ),
    },
]

# ─────────────────────────────────────────────
#  APP INSTANCE
# ─────────────────────────────────────────────
app = FastAPI(
    title="Price Surge API",
    description="""
## Zomato Dynamic Pricing Intelligence — Bhubaneswar

An end-to-end data pipeline that scrapes live menu prices across **19 restaurants**,
pairs every observation with real weather data, and runs **proper statistical tests**
to answer one question:

> *Do restaurant owners quietly raise menu prices when the weather turns bad?*

### Architecture
- **Scraper:** Playwright (headless=False, iPhone 13 Pro emulation, `__PRELOADED_STATE__` extraction)
- **Database:** PostgreSQL → Supabase (cloud)
- **Scheduler:** Python scheduler at 7 fixed clock slots per day
- **Analytics:** Mann-Whitney U, Kruskal-Wallis, Pearson correlation, Z-score normalization
- **Dashboard:** Power BI (8 pages, dark theme)

### Data scope
`72K+ rows` across 19 restaurants · 5 food categories · ~2 months of collection

### Key finding
Dynamic pricing is **highly concentrated** — not a market-wide norm.

---
Built by [Laren Sahu](https://laren27.github.io/Price-Surge/) · Source on [GitHub](https://github.com/Laren27/Price-Surge)
    """,
    version="1.0.0",
    contact={
        "name": "Laren Sahu",
        "url": "https://laren27.github.io/Price-Surge/",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    docs_url=None,      # disable default docs — we serve custom below
    redoc_url="/redoc", # keep redoc as fallback
)

# ─────────────────────────────────────────────
#  CORS
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  ROUTERS
# ─────────────────────────────────────────────
app.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
app.include_router(analysis.router,    prefix="/analysis",    tags=["analysis"])


# ─────────────────────────────────────────────
#  CUSTOM SWAGGER UI
#  Overrides the default Swagger theme with
#  the Price Surge Power BI color palette.
# ─────────────────────────────────────────────
CUSTOM_SWAGGER_CSS = """
/* ── DESIGN TOKENS — Price Surge Power BI palette ── */
:root {
  --bg:        #06101F;
  --surface:   #0C1B35;
  --surface2:  #0E1E33;
  --red:       #E23744;
  --blue:      #2D7DD2;
  --teal:      #00C9A7;
  --amber:     #F5A623;
  --purple:    #9B7FE8;
  --text:      #E8EDF2;
  --text-muted:rgba(232,237,242,0.55);
  --border:    rgba(255,255,255,0.08);
  --mono:      'JetBrains Mono', 'Fira Mono', monospace;
}

/* ── BASE ── */
body, .swagger-ui {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'DM Sans', -apple-system, sans-serif !important;
}

/* ── TOP BAR ── */
.swagger-ui .topbar {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 10px 24px !important;
}
.swagger-ui .topbar .download-url-wrapper input[type=text] {
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-muted) !important;
  border-radius: 6px !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
}
.swagger-ui .topbar a { display: none !important; } /* hide default Swagger logo */

/* ── INFO BLOCK (title / description) ── */
.swagger-ui .info {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 28px 32px !important;
  margin: 24px 0 !important;
}
.swagger-ui .info .title {
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
  font-size: 28px !important;
  font-weight: 700 !important;
  letter-spacing: -0.5px !important;
}
.swagger-ui .info .title small {
  background: var(--red) !important;
  color: #fff !important;
  border-radius: 4px !important;
  padding: 2px 8px !important;
  font-size: 12px !important;
  font-family: var(--mono) !important;
  margin-left: 10px !important;
  vertical-align: middle !important;
}
.swagger-ui .info p,
.swagger-ui .info li,
.swagger-ui .info blockquote {
  color: var(--text-muted) !important;
  font-size: 14px !important;
  line-height: 1.7 !important;
}
.swagger-ui .info blockquote {
  border-left: 3px solid var(--red) !important;
  padding-left: 14px !important;
  font-style: italic !important;
  color: var(--text) !important;
}
.swagger-ui .info a {
  color: var(--blue) !important;
  text-decoration: none !important;
}
.swagger-ui .info a:hover { text-decoration: underline !important; }
.swagger-ui .info h2, .swagger-ui .info h3 {
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  margin-top: 20px !important;
  border-bottom: 1px solid var(--border) !important;
  padding-bottom: 6px !important;
}
.swagger-ui .info strong { color: var(--text) !important; }

/* ── TAG SECTIONS ── */
.swagger-ui .opblock-tag {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  margin-bottom: 8px !important;
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  padding: 12px 20px !important;
}
.swagger-ui .opblock-tag:hover {
  background: rgba(45,125,210,0.10) !important;
}
.swagger-ui .opblock-tag-section p {
  color: var(--text-muted) !important;
  font-size: 13px !important;
  padding: 0 20px 12px !important;
  margin: 0 !important;
}

/* ── ENDPOINT BLOCKS ── */
.swagger-ui .opblock {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  margin-bottom: 6px !important;
}
.swagger-ui .opblock .opblock-summary {
  border-radius: 8px !important;
  padding: 10px 16px !important;
}
.swagger-ui .opblock .opblock-summary:hover {
  background: rgba(255,255,255,0.03) !important;
}

/* GET — Blue */
.swagger-ui .opblock.opblock-get {
  border-left: 3px solid var(--blue) !important;
}
.swagger-ui .opblock.opblock-get .opblock-summary-method {
  background: var(--blue) !important;
  color: #fff !important;
  border-radius: 4px !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 0.5px !important;
  min-width: 54px !important;
  text-align: center !important;
}

/* POST — Red */
.swagger-ui .opblock.opblock-post {
  border-left: 3px solid var(--red) !important;
}
.swagger-ui .opblock.opblock-post .opblock-summary-method {
  background: var(--red) !important;
  color: #fff !important;
  border-radius: 4px !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  min-width: 54px !important;
  text-align: center !important;
}

/* ── ENDPOINT PATH & DESCRIPTION ── */
.swagger-ui .opblock-summary-path {
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
}
.swagger-ui .opblock-summary-description {
  color: var(--text-muted) !important;
  font-size: 13px !important;
}
.swagger-ui .opblock-description-wrapper p {
  color: var(--text-muted) !important;
  font-size: 13px !important;
  line-height: 1.6 !important;
  padding: 12px 20px !important;
}

/* ── RESPONSE / SCHEMA BLOCKS ── */
.swagger-ui .responses-inner,
.swagger-ui .response-col_description,
.swagger-ui table.responses-table {
  background: var(--bg) !important;
  color: var(--text-muted) !important;
}
.swagger-ui .response-col_status { color: var(--teal) !important; font-family: var(--mono) !important; }
.swagger-ui table thead tr th { color: var(--text-muted) !important; border-color: var(--border) !important; }
.swagger-ui table tbody tr td { border-color: var(--border) !important; color: var(--text-muted) !important; }

/* ── CODE / EXAMPLE BLOCKS ── */
.swagger-ui .highlight-code pre,
.swagger-ui .microlight,
.swagger-ui textarea,
.swagger-ui .body-param__text {
  background: var(--bg) !important;
  color: var(--teal) !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
}

/* ── EXECUTE BUTTON ── */
.swagger-ui .btn.execute {
  background: var(--red) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 6px !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 8px 20px !important;
  cursor: pointer !important;
}
.swagger-ui .btn.execute:hover { opacity: 0.85 !important; }

/* ── AUTHORIZE BUTTON ── */
.swagger-ui .btn.authorize {
  border: 1px solid var(--blue) !important;
  color: var(--blue) !important;
  border-radius: 6px !important;
  background: transparent !important;
}

/* ── MODELS SECTION ── */
.swagger-ui section.models {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
.swagger-ui section.models h4 {
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
}
.swagger-ui .model-title { color: var(--amber) !important; font-family: var(--mono) !important; }
.swagger-ui .model { color: var(--text-muted) !important; }
.swagger-ui .prop-type { color: var(--purple) !important; font-family: var(--mono) !important; }
.swagger-ui .prop-format { color: var(--teal) !important; font-family: var(--mono) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }

/* ── MISC ── */
.swagger-ui select {
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
}
.swagger-ui input[type=text], .swagger-ui input[type=email], .swagger-ui input[type=password] {
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
}
.swagger-ui .dialog-ux .modal-ux {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}
"""

CUSTOM_SWAGGER_JS = """
// Inject Syne + DM Sans + JetBrains Mono from Google Fonts
const link = document.createElement('link');
link.rel = 'stylesheet';
link.href = 'https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap';
document.head.appendChild(link);
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    """Serve Swagger UI with the Price Surge dark theme."""
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Price Surge API · Docs",
        swagger_favicon_url="https://laren27.github.io/Price-Surge/favicon.ico",
    )
    # Inject custom CSS + JS into the returned HTML
    patched = html.body.decode("utf-8").replace(
        "</head>",
        f"<style>{CUSTOM_SWAGGER_CSS}</style><script>{CUSTOM_SWAGGER_JS}</script></head>",
    )
    return HTMLResponse(content=patched, status_code=200)


# ─────────────────────────────────────────────
#  ROOT
# ─────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "project": "Price Surge",
        "description": "Zomato dynamic pricing intelligence — Bhubaneswar",
        "docs": "/docs",
        "redoc": "/redoc",
        "landing": "https://laren27.github.io/Price-Surge/",
    }