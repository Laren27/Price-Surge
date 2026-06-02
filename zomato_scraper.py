# zomato_scraper.py

from playwright.sync_api import sync_playwright
from datetime import datetime
import time, json, random, csv, os

# ─────────────────────────────────────────────
# RESTAURANTS LIST

RESTAURANTS = [
    # BIRYANI
    ("https://www.zomato.com/bhubaneswar/biriyani-box-sahid-nagar-bhubaneshwar/order", "Biriyani Box", "biryani"),
    ("https://www.zomato.com/bhubaneswar/biryani-by-kilo-chandrasekharpur-bhubaneshwar/order", "Biryani By Kilo", "biryani"),
    ("https://www.zomato.com/bhubaneswar/behrouz-biryani-patia-bhubaneshwar/order", "Behrouz Biryani", "biryani"),
    ("https://www.zomato.com/bhubaneswar/mughlai-house-1-patia-bhubaneshwar/order", "Mughlai House", "biryani"),

    # MOMOS
    ("https://www.zomato.com/bhubaneswar/wow-momo-patia-bhubaneshwar/order", "Wow! Momo", "momos"),
    ("https://www.zomato.com/bhubaneswar/burnt-patia-bhubaneshwar/order", "Burnt", "momos"),
    ("https://www.zomato.com/bhubaneswar/bobs-momo-patia-bhubaneshwar/order", "Bob's Momo", "momos"),
    ("https://www.zomato.com/bhubaneswar/taste-of-china-chandrasekharpur-bhubaneshwar/order", "Taste of China", "momos"),
    ("https://www.zomato.com/bhubaneswar/darjeeling-kitchen-patia-bhubaneshwar/order", "Darjeeling Kitchen", "biryani"),

    # FRIED CHICKEN / BURGERS
    ("https://www.zomato.com/bhubaneswar/kfc-2-patia-bhubaneshwar/order", "KFC", "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/burger-king-1-patia-bhubaneshwar/order", "Burger King", "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/biggies-burger-patia-bhubaneshwar/order", "Biggies Burger", "fried_chicken"),
    ("https://www.zomato.com/bhubaneswar/burger-singh-big-punjabi-burgers-patia-bhubaneshwar/order", "Burger Singh", "fried_chicken"),

    # ROLLS
    ("https://www.zomato.com/bhubaneswar/faasos-wraps-rolls-shawarma-patia-bhubaneshwar/order", "Faasos", "rolls"),
    ("https://www.zomato.com/bhubaneswar/rolls-world-chandrasekharpur-bhubaneshwar/order", "Rolls World", "rolls"),
    ("https://www.zomato.com/bhubaneswar/zam-zam-grills-patia-bhubaneshwar/order", "Zam Zam Grills", "rolls"),

    # NORTH INDIAN / PANEER
    ("https://www.zomato.com/bhubaneswar/truptee-legacy-patia-bhubaneshwar/order", "Truptee Legacy", "paneer"),
    ("https://www.zomato.com/bhubaneswar/mughlai-house-1-patia-bhubaneshwar/order", "Mughlai House", "paneer"),
    ("https://www.zomato.com/bhubaneswar/kake-di-hatti-patia-bhubaneshwar/order", "Kake Di Hatti", "paneer"),
    ("https://www.zomato.com/bhubaneswar/kake-da-minar-chandrasekharpur-bhubaneshwar/order", "Kake Da Minar", "paneer"),
]

# ─────────────────────────────────────────────
# COOKIE CHECK

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

def fetch_live_pricing(url, restaurant_name, category):
    results = []

    try:
        with open("zomato_cookies.json") as f:
            saved_cookies = json.load(f)
    except FileNotFoundError:
        print("❌ zomato_cookies.json not found — run save_cookies.py first")
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

        # Check session
        print("Checking session...")
        page.goto("https://www.zomato.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        if not check_cookies_valid(page):
            print("⚠️ Cookies expired — re-run save_cookies.py")
            browser.close()
            return []
        print("✅ Session valid")

        # Load restaurant page
        print(f"Loading menu for {restaurant_name}...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)

        # Scroll to bottom
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

