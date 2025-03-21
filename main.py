import asyncio
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from persiantools.jdatetime import JalaliDate
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

previous_gold_price = None
previous_tether_price = None

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

def get_gold_price():
    url = 'https://milli.gold/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    price_element = soup.select_one('p.font-bold.text-title1')
    return price_element.text.strip() if price_element else '0'

def get_tether_price():
    url = 'https://nobitex.ir/usdt/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    price_element = soup.select_one('div.text-headline-medium')
    return price_element.text.strip() if price_element else '0'

async def main():
    global previous_gold_price, previous_tether_price

    while True:
        try:
            gold_price = get_gold_price()
            tether_price = get_tether_price()

            gold_price_with_arrow = add_arrow("قیمت لحظه‌ای طلا:", gold_price, previous_gold_price)
            tether_price_with_arrow = add_arrow("قیمت تتر:", tether_price, previous_tether_price, is_tether=True)

            await send_price_to_telegram(gold_price_with_arrow, tether_price_with_arrow)

            previous_gold_price = gold_price
            previous_tether_price = tether_price

            print(f"ارسال شد | طلا: {gold_price} | تتر: {tether_price}")
        except Exception as e:
            print(f"خطا: {e}")

        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
