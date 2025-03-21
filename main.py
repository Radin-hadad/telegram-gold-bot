import asyncio
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot
from telegram.error import TelegramError
import re
from persiantools.jdatetime import JalaliDate
from fastapi import FastAPI
import uvicorn
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# مرورگر رو به صورت Lazy load می‌کنیم که فقط یک بار باز شه
driver = None

def get_driver():
    global driver
    if driver is None:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def extract_number(price_text):
    numbers = re.findall(r'\d+', price_text.replace(',', ''))
    return int(''.join(numbers)) if numbers else 0

def convert_to_english_numbers(text):
    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    english_numbers = '0123456789'
    translation_table = str.maketrans(''.join(persian_numbers), ''.join(english_numbers))
    return text.translate(translation_table)

def add_comma_to_number(number):
    return "{:,}".format(number)

def add_arrow(title, current_price_text, previous_price_text, is_tether=False):
    current_price_text = convert_to_english_numbers(current_price_text)
    current_num = extract_number(current_price_text)

    if not is_tether:
        current_num = current_num // 10

    if previous_price_text is None:
        return f"🔹 {title} {add_comma_to_number(current_num)} تومان"

    previous_num = extract_number(previous_price_text)
    arrow = "🔺" if current_num > previous_num else "🔻" if current_num < previous_num else "🔹"

    return f"{arrow} {title} {add_comma_to_number(current_num)} تومان"

async def send_price_to_telegram(gold_price, tether_price):
    bot = Bot(token=TOKEN)
    current_time = datetime.now().strftime('%H:%M')
    current_date = JalaliDate.today().strftime('%Y/%m/%d')
    current_time = convert_to_english_numbers(current_time)
    current_date = convert_to_english_numbers(current_date)
    message = f"<b>{gold_price}\n{tether_price}\n</b>\nساعت: {current_time}\nتاریخ: {current_date}<b>\nمیلی‌گلد مرجع قیمت طلا</b>"
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")
    except TelegramError as e:
        print(f"خطا در ارسال پیام: {e}")

async def get_gold_price():
    d = get_driver()
    d.get('https://milli.gold/')
    price_element = WebDriverWait(d, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'p.font-bold.text-title1.leading-title1.text-deepOcean-focus.md\\:text-headLine3.md\\:leading-headLine3.lg\\:text-headLine2.lg\\:leading-headLine2'))
    )
    return price_element.text.strip()

async def get_tether_price():
    d = get_driver()
    d.get('https://nobitex.ir/usdt/')
    price_element = WebDriverWait(d, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.text-headline-medium.text-txt-neutral-default.dark\\:text-txt-neutral-default.desktop\\:text-headline-large'))
    )
    return price_element.text.strip()

previous_gold_price = None
previous_tether_price = None

async def loop_prices():
    global previous_gold_price, previous_tether_price
    while True:
        try:
            gold_price = await get_gold_price()
            tether_price = await get_tether_price()

            gold_price_with_arrow = add_arrow("قیمت لحظه‌ای طلا:", gold_price, previous_gold_price)
            tether_price_with_arrow = add_arrow("قیمت تتر:", tether_price, previous_tether_price, is_tether=True)

            await send_price_to_telegram(gold_price_with_arrow, tether_price_with_arrow)

            previous_gold_price = gold_price
            previous_tether_price = tether_price

            print(f"ارسال شد | طلا: {gold_price} | تتر: {tether_price}")
        except Exception as e:
            print(f"خطا در حلقه: {e}")

        await asyncio.sleep(300)

# FastAPI app for Render
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ربات میلی‌گلد فعال است 🚀"}

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(loop_prices())
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
