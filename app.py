import telebot
import requests
import os
import uuid
from telebot import types

# --- токены ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

bot = telebot.TeleBot(TOKEN)

# --- цены (рубли) ---
prices = {
    "25": 35,
    "50": 75,
    "100": 125,
    "150": 175,
    "200": 225,
    "300": 325
}

# --- главное меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 Профиль", "⭐ Купить звезды")
    markup.add("⚙️ Настройки")
    return markup

# --- старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать!\nВыберите действие:",
        reply_markup=main_menu()
    )

# --- профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    bot.send_message(
        message.chat.id,
        f"👤 Профиль\n\nID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'нет'}",
        reply_markup=main_menu()
    )

# --- меню покупки ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for stars, price in prices.items():
        markup.add(f"{stars} ⭐ — {price} ₽")

    markup.add("⬅️ Назад")

    bot.send_message(message.chat.id, "Выберите пакет:", reply_markup=markup)

# --- назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "Главное меню", reply_markup=main_menu())

# --- создание платежа ЮKassa ---
def create_payment(amount_rub, user_id):
    url = "https://api.yookassa.ru/v3/payments"

    headers = {
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4())
    }

    data = {
        "amount": {
            "value": str(amount_rub),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot_username"
        },
        "capture": True,
        "description": f"{amount_rub} RUB | user {user_id}"
    }

    r = requests.post(
        url,
        json=data,
        headers
