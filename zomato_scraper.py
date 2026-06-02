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

