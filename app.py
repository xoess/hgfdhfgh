import telebot
from telebot import types
import requests
import os

# --- настройки ---
TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

ADMIN_IDS = [7315281700]

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

# --- картинки ---
IMG_WELCOME = "https://imglink.cc/cdn/K3tbrvOvzl.jpg"
IMG_PROFILE = "https://imglink.cc/cdn/OZmDy2H4iI.jpg"
IMG_STARS   = "https://imglink.cc/cdn/_RxgFRvwh9.jpg"

# --- меню ---
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить звезды", "👤 Профиль")
    kb.add("⚙️ Настройки")
    return kb

# --- старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_photo(
        message.chat.id,
        IMG_WELCOME,
        caption=(
            "👋 <b>Добро пожаловать в Aulshop!</b>\n\n"
            f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
            "Выберите действие 👇"
        ),
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# --- профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    bot.send_photo(
        message.chat.id,
        IMG_PROFILE,
        caption=(
            "👤 <b>Ваш профиль</b>\n\n"
            f"🆔 ID: <code>{message.from_user.id}</code>\n"
            f"👤 Username: @{message.from_user.username or 'нет'}"
        ),
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# --- выбор пакета ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def choose_stars(message):
    kb = types.InlineKeyboardMarkup()
    for stars, price in prices.items():
        kb.add(types.InlineKeyboardButton(
            f"{stars} ⭐ — {price} ₽",
            callback_data=f"buy_{stars}"
        ))

    bot.send_photo(
        message.chat.id,
        IMG_STARS,
        caption="⭐ <b>Выберите пакет</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- выбор оплаты ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def choose_payment(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер / СБП", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 CryptoBot", callback_data=f"crypto_{amount}"))

    bot.edit_message_caption(
        caption=f"⭐ <b>{amount} Stars</b>\n💰 {price} ₽\n\nВыберите оплату:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

# --- СБЕР ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber_pay(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    CARD = "2200 1234 5678 9012"
    PHONE = "+79991234567"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(
        call.message.chat.id,
        f"""
💳 <b>Оплата Сбер / СБП</b>

💰 Сумма: <b>{price} ₽</b>

📱 СБП:+79330270826

💳 Карта:2202208225487652

После оплаты нажмите кнопку ниже
""",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- CRYPTOBOT ---
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
        bot.send_message(call.message.chat.id, "❌ Ошибка оплаты")
        return

    pay_url = r["result"]["pay_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Оплатить", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(call.message.chat.id, "💎 Оплата криптой:", reply_markup=kb)

# --- проверка ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(call):
    amount = call.data.split("_")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{call.from_user.id}_{amount}"
    ))

    for admin in ADMIN_IDS:
        bot.send_message(
            admin,
            f"💰 Оплата\n👤 @{call.from_user.username}\n⭐ {amount}",
            reply_markup=kb
        )

    bot.send_message(call.message.chat.id, "⏳ Ждите подтверждение...")

# --- подтверждение ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(call):
    user_id, amount = call.data.split("_")[1:]

    bot.send_message(
        int(user_id),
        f"✅ Оплата подтверждена!\n⭐ {amount} придут в течение 5 минут"
    )

    bot.answer_callback_query(call.id, "Готово")

# --- запуск ---
bot.infinity_polling(skip_pending=True)