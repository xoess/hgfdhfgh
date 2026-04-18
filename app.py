
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
@bot.message_handler(commands=['start'])
def start(msg):
    kb = telebot.types.InlineKeyboardMarkup()
    for k, v in prices.items():
        kb.add(telebot.types.InlineKeyboardButton(
            f"⭐ {k} — {v}₽",
            callback_data=f"buy_{k}"
        ))
    bot.send_message(msg.chat.id, "💫 Выбери пакет:", reply_markup=kb)

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

bot.polling()
