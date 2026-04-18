
import telebot
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


bot = telebot.TeleBot(TOKEN)

prices = {
    "25": 30,
    "50": 75,
    "100": 125,
    "150": 170,
    "200": 215,
    "300": 350
}

# --- старт ---

# --- покупка ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(call):
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
        bot.send_message(call.message.chat.id, "❌ Ошибка создания оплаты")
        return

    pay_url = r["result"]["pay_url"]

    # отправляем пользователю
    bot.send_message(
        call.message.chat.id,
        f"💳 Оплати здесь:\n{pay_url}\n\n"
        f"После оплаты нажми кнопку ниже 👇"
    )

    # кнопка "Я оплатил"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton(
        "✅ Я оплатил",
        callback_data=f"check_{amount}"
    ))

    bot.send_message(call.message.chat.id, "Подтверди оплату:", reply_markup=kb)

# --- уведомление админа ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(call):
    amount = call.data.split("_")[1]

    bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь @{call.from_user.username} "
        f"(ID: {call.from_user.id}) говорит, что оплатил {amount} ⭐"
    )

    bot.send_message(
        call.message.chat.id,
        "⏳ Проверяем оплату, подожди..."
    )
from telebot import types

# --- Главное меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("👤 Профиль")
    btn2 = types.KeyboardButton("⭐ Купить звезды")
    btn3 = types.KeyboardButton("⚙️ Настройки")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup


# --- Старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать!\nВыберите действие:",
        reply_markup=main_menu()
    )


# --- Профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    user_id = message.from_user.id
    username = message.from_user.username

    text = f"""
👤 Ваш профиль:

🆔 ID: {user_id}
📛 Username: @{username if username else 'нет'}
"""

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


# --- Покупка ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for stars, price in prices.items():
        markup.add(types.KeyboardButton(f"{stars} ⭐ — {price} ₽"))

    markup.add(types.KeyboardButton("⬅️ Назад"))

    bot.send_message(message.chat.id, "Выберите пакет:", reply_markup=markup)


# --- Настройки ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings(message):
    bot.send_message(
        message.chat.id,
        "⚙️ Настройки пока в разработке",
        reply_markup=main_menu()
    )


# --- Назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "🔙 Главное меню", reply_markup=main_menu())
    @bot.message_handler(func=lambda m: "⭐" in m.text and "₽" in m.text)
def process_buy(message):
    try:
        amount = message.text.split(" ")[0]
        price = prices[amount]

        url = "https://pay.crypt.bot/api/createInvoice"
        headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}

        data = {
            "asset": "USDT",
            "amount": price / 100,
            "description": f"{amount} stars",
            "payload": str(message.from_user.id)
        }

        r = requests.post(url, headers=headers, json=data).json()

        if not r.get("ok"):
            bot.send_message(message.chat.id, "❌ Ошибка оплаты")
            return

        pay_url = r["result"]["pay_url"]

        bot.send_message(
            message.chat.id,
            f"💳 Оплати:\n{pay_url}"
        )

        bot.send_message(
            ADMIN_ID,
            f"💰 Новый заказ {amount} ⭐ от @{message.from_user.username}"
        )

    except:
        bot.send_message(message.chat.id, "Ошибка")
    
bot.polling()
