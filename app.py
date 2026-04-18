import telebot
from telebot import types
import requests
import os
import uuid

# --- ENV ---
TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

# --- цены ---
prices = {
    "25": 30,
    "50": 75,
    "100": 125,
    "150": 175,
    "200": 225,
    "300": 325
}

# --- меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("👤 Профиль"),
        types.KeyboardButton("⭐ Купить звезды")
    )
    markup.add(types.KeyboardButton("⚙️ Настройки"))
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
        f"👤 Профиль:\nID: {message.from_user.id}\nUsername: @{message.from_user.username}",
        reply_markup=main_menu()
    )

# --- настройки ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings(message):
    bot.send_message(
        message.chat.id,
        "⚙️ В разработке",
        reply_markup=main_menu()
    )

# --- выбор пакета ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def choose_stars(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for stars, price in prices.items():
        markup.add(types.KeyboardButton(f"{stars} ⭐ — {price} ₽"))

    markup.add(types.KeyboardButton("⬅️ Назад"))

    bot.send_message(message.chat.id, "Выберите пакет:", reply_markup=markup)

# --- назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "Главное меню", reply_markup=main_menu())

# --- выбор оплаты ---
@bot.message_handler(func=lambda m: "⭐ —" in m.text)
def choose_payment(message):
    amount = message.text.split()[0]
    price = prices.get(amount)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💎 CryptoBot", callback_data=f"crypto_{amount}"),
        types.InlineKeyboardButton("💳 Карта / СБП", callback_data=f"yoo_{amount}")
    )

    bot.send_message(
        message.chat.id,
        f"Вы выбрали {amount} ⭐ за {price}₽\nВыберите способ оплаты:",
        reply_markup=markup
    )

# --- CryptoBot ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def crypto_pay(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}

    data = {
        "asset": "USDT",
        "amount": price / 100,
        "description": f"{amount} stars",
        "payload": str(call.from_user.id)
    }

    r = requests.post(url, headers=headers, json=data).json()

    if not r.get("ok"):
        bot.send_message(call.message.chat.id, "❌ Ошибка крипто оплаты")
        return

    pay_url = r["result"]["pay_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Оплатить криптой", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data="check"))

    bot.send_message(
        call.message.chat.id,
        "Нажми кнопку для оплаты 👇",
        reply_markup=kb
    )

# --- ЮKassa ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("yoo_"))
def yoo_pay(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    url = "https://api.yookassa.ru/v3/payments"

    headers = {
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4())
    }
    data = {
        "amount": {
            "value": str(price),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot"
        },
        "capture": True,
        "description": f"{amount} stars | user {call.from_user.id}"
    }

    r = requests.post(
        url,
        json=data,
        headers=headers,
        auth=(SHOP_ID, SECRET_KEY)
    ).json()

    if not r.get("confirmation"):
        bot.send_message(call.message.chat.id, "❌ Ошибка ЮKassa")
        return

    pay_url = r["confirmation"]["confirmation_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Оплатить картой / СБП", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data="check"))

    bot.send_message(
        call.message.chat.id,
        "Нажми кнопку для оплаты 👇",
        reply_markup=kb
    )

# --- подтверждение ---
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь @{call.from_user.username} (ID: {call.from_user.id}) нажал 'оплатил'"
    )

    bot.send_message(
        call.message.chat.id,
        "⏳ Проверяем оплату..."
    )

# --- запуск ---
bot.polling(none_stop=True)
