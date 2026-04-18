import telebot
from telebot import types
import requests
import os

# --- ENV ---
TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

# --- цены ---
prices = {
    "25": 35,
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

    bot.send_message(call.message.chat.id, "Оплати и нажми кнопку 👇", reply_markup=kb)

# --- ЮMoney (готовый кошелек) ---
def create_yoomoney_link(amount, user_id):
    receiver = "4100119516144115"

    url = "https://yoomoney.ru/quickpay/confirm.xml"

    params = {
        "receiver": receiver,
        "quickpay-form": "shop",
        "targets": f"{amount} stars",
        "paymentType": "AC",
        "sum": amount,
        "label": str(user_id)
    }

    return url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])

@bot.callback_query_handler(func=lambda c: c.data.startswith("yoo_"))
def yoomoney_pay(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    pay_url = create_yoomoney_link(price, call.from_user.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Оплатить картой / СБП", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data="check"))

    bot.send_message(call.message.chat.id, "Оплати и нажми кнопку 👇", reply_markup=kb)

# --- пользователь нажал оплатил ---
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    user_id = call.from_user.id
    username = call.from_user.username

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить оплату",
        callback_data=f"accept_{user_id}"
    ))

    bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь @{username} (ID: {user_id}) оплатил?",
        reply_markup=kb
    )

    bot.send_message(
        call.message.chat.id,
        "⏳ Ожидаем подтверждение администратора..."
    )

# --- админ подтверждает ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def accept_payment(call):
    user_id = int(call.data.split("_")[1])

    bot.send_message(
        user_id,
        "✅ Оплата подтверждена!\n📦 Товар придет в течение 5 минут."
    )

    bot.send_message(
        call.message.chat.id,
        "✔️ Оплата подтверждена"
    )

# --- запуск ---
bot.infinity_polling()
