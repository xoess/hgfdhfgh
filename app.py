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

# --- ТВОИ КАРТИНКИ ---
IMG_MAIN = "AgACAgIAAxkBAAFHfEJp414ILgFPZIHifeOyuZ91oeZisAACQBRrGwUTIEvx4itiwJkrVgEAAwIAA3MAAzsE"
IMG_PROFILE = "AgACAgIAAxkBAAFHfEhp414mwl9xrct8OAe7IlWYYm765AACQhRrGwUTIEuE_EUM3sPNPQEAAwIAA20AAzsE"
IMG_STARS = "AgACAgIAAxkBAAFHfExp4143555vDfUCWXuQYf6ivlH8qAACQxRrGwUTIEvn6IWhnnNfXgEAAwIAA3kAAzsE"

# --- меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⭐ Купить звезды", "👤 Профиль")
    markup.add("📦 Мои заказы")
    return markup

# --- старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_photo(
        message.chat.id,
        IMG_MAIN,
        caption=(
            "💎 <b>STAR SHOP</b>\n\n"
            "⚡ Быстрая покупка Telegram Stars\n"
            "🔒 Безопасно • Мгновенно • Удобно\n\n"
            "👇 Выберите действие"
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
            f"👤 Username: @{message.from_user.username or 'нет'}\n\n"
            "💬 Статус: Клиент"
        ),
        parse_mode="HTML"
    )

# --- заказы ---
@bot.message_handler(func=lambda m: m.text == "📦 Мои заказы")
def orders(message):
    bot.send_message(message.chat.id, "📦 У вас пока нет заказов")

# --- выбор пакета ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def choose_package(message):
    markup = types.InlineKeyboardMarkup()

    for stars, price in prices.items():
        markup.add(types.InlineKeyboardButton(
            f"{stars} ⭐ — {price} ₽",
            callback_data=f"buy_{stars}"
        ))

    bot.send_photo(
        message.chat.id,
        IMG_STARS,
        caption="⭐ <b>Выберите пакет</b>",
        parse_mode="HTML",
        reply_markup=markup
    )

# --- выбор оплаты ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def choose_payment(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💳 Карта / СБП", callback_data=f"yoo_{amount}")
    )
    markup.add(
        types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}")
    )

    bot.send_message(
        call.message.chat.id,
        f"⭐ {amount} Stars\n💰 {price} ₽\n\nВыберите способ оплаты:",
        reply_markup=markup
    )

# --- ЮMoney ---
def yoomoney_link(amount, user_id):
    return (
        "https://yoomoney.ru/quickpay/confirm.xml?"
        f"receiver=4100119516144115&quickpay-form=shop"
        f"&targets={amount}+stars&paymentType=AC"
        f"&sum={amount}&label={user_id}"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("yoo_"))
def yoo_pay(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    pay_url = yoomoney_link(price, call.from_user.id)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Оплатить", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data="check"))

    bot.send_message(call.message.chat.id, "💳 Оплата:", reply_markup=kb)

# --- Crypto ---
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
        bot.send_message(call.message.chat.id, "❌ Ошибка")
        return

    pay_url = r["result"]["pay_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Оплатить", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data="check"))

    bot.send_message(call.message.chat.id, "💎 Оплата:", reply_markup=kb)

# --- проверка ---
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    user_id = call.from_user.id

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"accept_{user_id}"
    ))

    bot.send_message(
        ADMIN_ID,
        f"💰 Новый платёж от @{call.from_user.username}",
        reply_markup=kb
    )

    bot.send_message(call.message.chat.id, "⏳ Проверка...")

# --- подтверждение ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def accept(call):
    user_id = int(call.data.split("_")[1])

    bot.send_message(
        user_id,
        "✅ Оплата подтверждена!\n📦 Товар придет в течение 5 минут."
    )

    bot.send_message(call.message.chat.id, "✔️ Готово")

# --- запуск ---
bot.infinity_polling()