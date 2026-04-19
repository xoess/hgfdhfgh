import telebot
from telebot import types
import sqlite3
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

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
    banned INTEGER DEFAULT 0,
    referrer INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS refs (
    user_id INTEGER,
    ref_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
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
def add_user(uid, ref=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (uid, ref))
        if ref:
            cursor.execute("INSERT INTO refs (user_id, ref_id) VALUES (?, ?)", (uid, ref))
        conn.commit()

def get_balance(uid):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()
    return r[0] if r else 0

def update_balance(uid, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

def get_ref(uid):
    cursor.execute("SELECT referrer FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()
    return r[0] if r else None

def is_banned(uid):
    cursor.execute("SELECT banned FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()
    return r and r[0] == 1

def has_active_order(uid):
    cursor.execute("SELECT * FROM orders WHERE user_id=? AND status!='done'", (uid,))
    return cursor.fetchone() is not None

def create_order(uid, amount):
    cursor.execute("INSERT INTO orders (user_id, amount, status) VALUES (?, ?, 'pending')", (uid, amount))
    conn.commit()
    return cursor.lastrowid

# ===== МЕНЮ =====
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить звезды", "👤 Профиль")
    kb.add("👥 Рефералы")
    return kb

# ===== СТАРТ =====
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    ref = None
    if len(m.text.split()) > 1:
        try:
            ref = int(m.text.split()[1])
            if ref == uid:
                ref = None
        except:
            ref = None

    add_user(uid, ref)

    bot.send_photo(uid, IMG_WELCOME,
                   caption=f"👋 Добро пожаловать в Aulshop!\n🆔 {uid}",
                   reply_markup=menu())

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = m.from_user.id

    cursor.execute("SELECT user_id FROM refs WHERE ref_id=?", (uid,))
    refs = cursor.fetchall()

    bot.send_photo(uid, IMG_PROFILE,
                   caption=f"👤 Профиль\n\n🆔 {uid}\n⭐ {get_balance(uid)}\n👥 {len(refs)}")

# ===== ПОКУПКА =====
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(m):
    kb = types.InlineKeyboardMarkup()
    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_photo(m.chat.id, IMG_STARS, caption="Выбери пакет", reply_markup=kb)

# ===== ВЫБОР =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    uid = c.from_user.id
    amount = int(c.data.split("_")[1])

    if has_active_order(uid):
        bot.answer_callback_query(c.id, "❌ У тебя есть активный заказ")
        return

    order_id = create_order(uid, amount)
    price = prices[str(amount)]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{order_id}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{order_id}"))

    bot.edit_message_caption(
        caption=f"📦 Заказ #{order_id}\n⭐ {amount} = {price}₽",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ===== СБЕР =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(c):
    order_id = int(c.data.split("_")[1])

    cursor.execute("SELECT amount FROM orders WHERE id=?", (order_id,))
    amount = cursor.fetchone()[0]
    price = prices[str(amount)]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{order_id}"))

    bot.send_message(c.message.chat.id,
                     f"📦 #{order_id}\n💳 {CARD_NUMBER}\n📱 {PHONE_NUMBER}\n💰 {price}₽",
                     reply_markup=kb)

# ===== CRYPTO (БЕЗ АВТО ПРОВЕРКИ) =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def crypto(c):
    order_id = int(c.data.split("_")[1])

    cursor.execute("SELECT amount FROM orders WHERE id=?", (order_id,))
    amount = cursor.fetchone()[0]
    price = prices[str(amount)]

    r = requests.post(
        "https://pay.crypt.bot/api/createInvoice",
        headers={"Crypto-Pay-API-Token": CRYPTO_TOKEN},
        json={"asset": "USDT", "amount": price / 100}
    ).json()

    url = r["result"]["pay_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Оплатить", url=url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{order_id}"))

    bot.send_message(c.message.chat.id,
                     f"📦 #{order_id}\nПосле оплаты нажми кнопку",
                     reply_markup=kb)

# ===== Я ОПЛАТИЛ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(c):
    order_id = int(c.data.split("_")[1])

    cursor.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
    uid = cursor.fetchone()[0]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{order_id}"))

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"💰 Заказ #{order_id}\n👤 {uid}", reply_markup=kb)

# ===== ПОДТВЕРЖДЕНИЕ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(c):
    order_id = int(c.data.split("_")[1])

    cursor.execute("SELECT user_id, amount FROM orders WHERE id=?", (order_id,))
    uid, amount = cursor.fetchone()

    cursor.execute("UPDATE orders SET status='confirmed' WHERE id=?", (order_id,))
    conn.commit()

    bot.send_message(uid, f"📦 #{order_id}\n⏳ В обработке")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Выдал", callback_data=f"done_{order_id}"))

    bot.edit_message_text(
        f"📦 #{order_id}\n👤 {uid}\n⭐ {amount}\n⏳ В обработке",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

# ===== ВЫДАЧА =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("done_"))
def done(c):
    order_id = int(c.data.split("_")[1])

    cursor.execute("SELECT user_id, amount FROM orders WHERE id=?", (order_id,))
    uid, amount = cursor.fetchone()

    cursor.execute("UPDATE orders SET status='done' WHERE id=?", (order_id,))
    conn.commit()

    bot.send_message(uid, f"📦 #{order_id}\n✅ Выполнен")

    ref = get_ref(uid)
    if ref:
        bonus = int(amount * 0.10)
        update_balance(ref, bonus)
        bot.send_message(ref, f"🎁 +{bonus}⭐")

    bot.edit_message_text(
        f"📦 #{order_id}\n👤 {uid}\n⭐ {amount}\n✅ Выполнен",
        c.message.chat.id,
        c.message.message_id
    )

# ===== ЗАПУСК =====
bot.infinity_polling(skip_pending=True)