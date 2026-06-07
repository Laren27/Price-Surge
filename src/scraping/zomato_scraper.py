# zomato_scraper.py

from playwright.sync_api import sync_playwright
from datetime import datetime
from pathlib import Path
import time, json, random, csv, os
import importlib.util

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# LOAD DATABASE MODULE
# ─────────────────────────────────────────────
def load_db_module():
    spec = importlib.util.spec_from_file_location(
        "database",
        str(Path(__file__).resolve().parent / "database.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_db            = load_db_module()
save_prices_db = _db.save_prices

# ─────────────────────────────────────────────
# RESTAURANTS LIST
# ─────────────────────────────────────────────
RESTAURANTS = [
    # BIRYANI
    ("https://www.zomato.com/bhubaneswar/biriyani-box-sahid-nagar-bhubaneshwar/order",         "Biriyani Box",       "biryani"),
    ("https://www.zomato.com/bhubaneswar/biryani-by-kilo-chandrasekharpur-bhubaneshwar/order", "Biryani By Kilo",    "biryani"),
    ("https://www.zomato.com/bhubaneswar/behrouz-biryani-patia-bhubaneshwar/order",            "Behrouz Biryani",    "biryani"),
    ("https://www.zomato.com/bhubaneswar/mughlai-house-1-patia-bhubaneshwar/order",            "Mughlai House",      "biryani"),

    # MOMOS
    ("https://www.zomato.com/bhubaneswar/wow-momo-patia-bhubaneshwar/order",                   "Wow! Momo",          "momos"),
    ("https://www.zomato.com/bhubaneswar/burnt-patia-bhubaneshwar/order",                      "Burnt",              "momos"),
    ("https://www.zomato.com/bhubaneswar/bobs-momo-patia-bhubaneshwar/order",                  "Bob's Momo",         "momos"),
    ("https://www.zomato.com/bhubaneswar/taste-of-china-chandrasekharpur-bhubaneshwar/order",  "Taste of China",     "momos"),
    ("https://www.zomato.com/bhubaneswar/darjeeling-kitchen-patia-bhubaneshwar/order",         "Darjeeling Kitchen", "momos"),

    # FRIED CHICKEN / BURGERS
    ("https://www.zomato.com/bhubaneswar/kfc-2-patia-bhubaneshwar/order",                                          "KFC",            "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/burger-king-1-patia-bhubaneshwar/order",                                  "Burger King",    "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/biggies-burger-patia-bhubaneshwar/order",                                 "Biggies Burger", "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/burger-singh-big-punjabi-burgers-patia-bhubaneshwar/order",               "Burger Singh",   "fried_chicken"),

    # ROLLS
    ("https://www.zomato.com/bhubaneswar/faasos-wraps-rolls-shawarma-patia-bhubaneshwar/order","Faasos",             "rolls"),
    ("https://www.zomato.com/bhubaneswar/rolls-world-chandrasekharpur-bhubaneshwar/order",     "Rolls World",        "rolls"),
    ("https://www.zomato.com/bhubaneswar/zam-zam-grills-patia-bhubaneshwar/order",             "Zam Zam Grills",     "rolls"),

    # NORTH INDIAN / PANEER
    ("https://www.zomato.com/bhubaneswar/truptee-legacy-patia-bhubaneshwar/order",             "Truptee Legacy",     "paneer"),
    ("https://www.zomato.com/bhubaneswar/kake-di-hatti-patia-bhubaneshwar/order",              "Kake Di Hatti",      "paneer"),
    ("https://www.zomato.com/bhubaneswar/kake-da-minar-chandrasekharpur-bhubaneshwar/order",   "Kake Da Minar",      "paneer"),
]

# ─────────────────────────────────────────────
# COOKIE CHECK
# ─────────────────────────────────────────────
def check_cookies_valid(page):
    try:
        return page.evaluate("""
            () => document.cookie.split(';').some(c =>
                c.trim().startsWith('zl=') ||
                c.trim().startsWith('zomato_user') ||
                c.trim().startsWith('PHPSESSID')
            )
        """)
    except Exception:
        return False

# ─────────────────────────────────────────────
# RECURSIVE ITEM EXTRACTOR
# ─────────────────────────────────────────────
def extract_items_recursive(data, depth=0):
    items = []
    if depth > 15:
        return items
    if isinstance(data, dict):
        name_val = price_val = None
        for k, v in data.items():
            kl = k.lower()
            if kl in ("name", "item_name", "dish_name", "title") and isinstance(v, str) and v:
                name_val = v
            if kl in ("price", "cost", "item_price", "display_price") and isinstance(v, (int, float)) and v > 0:
                price_val = str(int(v))
        if name_val and price_val:
            items.append({"item_name": name_val, "price": f"₹{price_val}"})
        for v in data.values():
            items.extend(extract_items_recursive(v, depth + 1))
    elif isinstance(data, list):
        for item in data:
            items.extend(extract_items_recursive(item, depth + 1))
    return items

# ─────────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────────
def fetch_live_pricing(url, restaurant_name, category, scrape_session_id):
    # ✅ scrape_session_id passed in from __main__
    # same session ID for all restaurants in one run
    results = []

    try:
        with open(PROJECT_ROOT / "zomato_cookies.json") as f:
            saved_cookies = json.load(f)
    except FileNotFoundError:
        print("[FAIL] zomato_cookies.json not found — run save_cookies.py first")
        return []

    with sync_playwright() as p:
        iphone = p.devices['iPhone 13 Pro']
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-http2',
            ]
        )
        context = browser.new_context(
            **iphone,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            permissions=["geolocation"],
            geolocation={"latitude": 20.2961, "longitude": 85.8245},
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'platform', { get: () => 'iPhone' });
            Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });
            window.chrome = undefined;
        """)

        context.add_cookies(saved_cookies)
        page = context.new_page()
        page.set_viewport_size({"width": 390, "height": 844})

        print("Checking session...")
        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto("https://www.zomato.com", wait_until="domcontentloaded", timeout=30000)
                break
            except Exception as e:
                if "ERR_NETWORK_CHANGED" in str(e) and attempt < MAX_RETRIES:
                    print(f"[WARN] Network blip on attempt {attempt}, retrying in 60s...")
                    time.sleep(60)
                else:
                    browser.close()
                    raise
        time.sleep(2)

        if not check_cookies_valid(page):
            print("[WARN] Cookies expired — re-run save_cookies.py")
            browser.close()
            return []
        print("[OK] Session valid")

        print(f"Loading menu for {restaurant_name}...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)

        print("Scrolling full menu...")
        while True:
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(1.2)
            pos = page.evaluate("window.scrollY")
            height = page.evaluate("document.body.scrollHeight")
            print(f"  {pos} / {height}")
            if pos + 844 >= height:
                break
        time.sleep(3)

        preloaded_raw = page.evaluate(r"""
            () => {
                const match = document.documentElement.innerHTML
                    .match(/window\.__PRELOADED_STATE__\s*=\s*JSON\.parse\("(.+?)"\);/s);
                return match ? match[1] : null;
            }
        """)

        if not preloaded_raw:
            print(f"[FAIL] __PRELOADED_STATE__ not found for {restaurant_name}")
            page.screenshot(path=str(PROJECT_ROOT / f"debug_{restaurant_name}.png"), full_page=True)
            browser.close()
            return []

        unescaped = preloaded_raw.encode('utf-8').decode('unicode_escape')
        state = json.loads(unescaped)
        raw_items = extract_items_recursive(state)
        print(f"Raw items before dedup: {len(raw_items)}")
        browser.close()

    # Deduplicate by name, keep last
    seen_names = {}
    for r in raw_items:
        seen_names[r["item_name"]] = r

    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    for item in seen_names.values():
        results.append({
            "restaurant":        restaurant_name,
            "category":          category,
            "item_name":         item["item_name"],
            "price":             item["price"],
            "scraped_at":        scraped_at,
            "scrape_session_id": scrape_session_id,  # ✅ same for all restaurants
        })

    return results

# ─────────────────────────────────────────────
# SAVE TO CSV (append mode)
# ─────────────────────────────────────────────
def save_to_csv(data, filepath=None):
    if filepath is None:
        filepath = RAW_DATA_DIR / "menu_prices.csv"
    if not data:
        return
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "restaurant", "category", "item_name",
            "price", "scraped_at", "scrape_session_id"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)
    print(f"[OK] Saved {len(data)} items to {filepath}")

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    all_data = []

    # ✅ Generate ONE session ID for this entire run
    # All 19 restaurants in this run share the same session ID
    # This links all prices to the same weather snapshot
    scrape_session_id = os.environ.get(
        "SCRAPE_SESSION_ID",
        datetime.now().strftime("%Y%m%d_%H%M")
    )
    print(f"Scrape session: {scrape_session_id}")
    for url, name, category in RESTAURANTS:
        print(f"\n{'='*50}")
        print(f"Scraping: {name} [{category}]")
        print(f"{'='*50}")

        items = fetch_live_pricing(url, name, category, scrape_session_id)
        all_data.extend(items)

        print(f"[OK] {len(items)} unique items for {name}")
        for item in items:
            print(f"  {item['item_name']} -> {item['price']}")

        if len(RESTAURANTS) > 1:
            delay = random.uniform(5, 10)
            print(f"Waiting {delay:.1f}s before next restaurant...")
            time.sleep(delay)

    save_to_csv(all_data)       # CSV backup
    save_prices_db(all_data)    # database