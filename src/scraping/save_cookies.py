# save_cookies.py — run this ONCE whenever cookies expire

from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.zomato.com/bhubaneswar/biriyani-box-sahid-nagar-bhubaneshwar/order")

    print("👉 Log in to Zomato manually in the browser window.")
    print("👉 Once you see the menu with prices, press Enter here.")
    input()

    cookies = context.cookies()
    with open("zomato_cookies.json", "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"✅ Saved {len(cookies)} cookies to zomato_cookies.json")
    browser.close()