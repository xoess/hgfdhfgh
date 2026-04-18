import telebot
from telebot import types
import sqlite3
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

# 🔥 НОВОЕ — берём с хоста
CARD_NUMBER = os.getenv("CARD_NUMBER") or "не указана"
PHONE_NUMBER = os.getenv("PHONE_NUMBER") or "не указан"

bot = telebot.TeleBot(TOKEN)
bot.delete_webhook()

# ===== БАЗА =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== НАСТРОЙКИ =====
ADMIN_IDS = [7315281700]

prices = {
    "10": 15,
    "25": 35,
    "50": 75,
    "75": 95,
    "100": 125,
    "150": 175,
    "200": 225,
    "300": 330
}

IMG_WELCOME = "https://imglink.cc/cdn/K3tbrvOvzl.jpg"
IMG_PROFILE = "https://imglink.cc/cdn/OZmDy2H4iI.jpg"
IMG_STARS = "https://imglink.cc/cdn/_RxgFRvwh9.jpg"

# ===== ФУНКЦИИ =====
def add_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit()

def get_balance(uid):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    return row[0] if row else 0

def update_balance(uid, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

def is_banned(uid):
    cursor.execute("SELECT banned FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()
    return r and r[0] == 1

# ===== МЕНЮ =====
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить звезды", "👤 Профиль")
    return kb

# ===== СТАРТ =====
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    add_user(uid)

    bot.send_photo(
        uid,
        IMG_WELCOME,
        caption=f"👋 Добро пожаловать в Aulshop!\n\n🆔 ID: {uid}\n⭐ Баланс: {get_balance(uid)}",
        reply_markup=menu()
    )

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    bot.send_photo(
        uid,
        IMG_PROFILE,
        caption=f"👤 Профиль\n\n🆔 {uid}\n⭐ Баланс: {get_balance(uid)}",
        reply_markup=menu()
    )

# ===== ПОКУПКА =====
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(m):
    kb = types.InlineKeyboardMarkup()

    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_photo(m.chat.id, IMG_STARS, caption="💰 Выберите пакет:", reply_markup=kb)

# выбор способа
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}"))
    kb.add(types.InlineKeyboardButton(f"⭐ Купить за {price}", callback_data=f"star_{amount}"))

    bot.edit_message_caption(
        caption=f"{amount}⭐ = {price}₽\n\nВыберите способ оплаты:",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ===== ОПЛАТА ЗА ЗВЕЗДЫ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("star_"))
def pay_star(c):
    uid = c.from_user.id
    amount = c.data.split("_")[1]
    price = prices[amount]

    if get_balance(uid) < price:
        bot.answer_callback_query(c.id, "❌ Недостаточно звёзд")
        return

    update_balance(uid, -price)
    bot.send_message(uid, f"✅ Куплено {amount}⭐")

# ===== СБЕР (ИСПОЛЬЗУЕТ ENV) =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(
        c.message.chat.id,
        f"💳 Оплата Сбер\n\n"
        f"💳 Карта: {CARD_NUMBER}\n"
        f"📱 Телефон: {PHONE_NUMBER}\n\n"
        f"Сумма: {price}₽\n\n"
        f"После оплаты нажми кнопку",
        reply_markup=kb
    )

# ===== CRYPTO =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def crypto(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    try:
        r = requests.post(
            "https://pay.crypt.bot/api/createInvoice",
            headers={"Crypto-Pay-API-Token": CRYPTO_TOKEN},
            json={"asset": "USDT", "amount": price / 100}
        ).json()

        url = r["result"]["pay_url"]

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💎 Оплатить", url=url))
        kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

        bot.send_message(c.message.chat.id, "💎 Оплата Crypto:", reply_markup=kb)

    except:
        bot.send_message(c.message.chat.id, "❌ Ошибка создания оплаты")

# ===== ПРОВЕРКА =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(c):
    amount = c.data.split("_")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{c.from_user.id}_{amount}"
    ))

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"💰 Оплата от {c.from_user.id}", reply_markup=kb)

    bot.send_message(c.from_user.id, "⏳ Ожидайте подтверждения")

# ===== ПОДТВЕРЖДЕНИЕ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(c):
    uid, amount = c.data.split("_")[1:]
    uid = int(uid)

    update_balance(uid, int(amount))

    bot.send_message(uid, f"✅ Оплата подтверждена\n⭐ Зачислено {amount}")
    bot.answer_callback_query(c.id, "Готово")

# ===== АДМИН =====
@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Выдать", "🚫 Бан", "✅ Разбан")

    bot.send_message(m.chat.id, "⚙ Админ панель", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Выдать")
def give(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    msg = bot.send_message(m.chat.id, "Введите: ID СУММА")
    bot.register_next_step_handler(msg, process_give)

def process_give(m):
    try:
        uid, amount = map(int, m.text.split())
        update_balance(uid, amount)
        bot.send_message(uid, f"🎁 Выдано {amount}⭐")
        bot.send_message(m.chat.id, "✅ Готово")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

@bot.message_handler(func=lambda m: m.text == "🚫 Бан")
def ban(m):
    msg = bot.send_message(m.chat.id, "Введите ID")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "🚫 Вы заблокированы")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

@bot.message_handler(func=lambda m: m.text == "✅ Разбан")
def unban(m):
    msg = bot.send_message(m.chat.id, "Введите ID")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "✅ Вы разблокированы")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

# ===== СТАРТ =====
bot.infinity_polling(skip_pending=True)
