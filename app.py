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

    bot.send_photo(
        uid,
        IMG_WELCOME,
        caption=f"👋 Добро пожаловать в Aulshop!\n\n🆔 ID: {uid}\n⭐ Баланс: {get_balance(uid)}",
        reply_markup=menu()
    )

# ===== ПРОФИЛЬ (ИСПРАВЛЕНО) =====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    cursor.execute("SELECT user_id FROM refs WHERE ref_id=?", (uid,))
    refs = cursor.fetchall()

    ref_count = len(refs)

    bot.send_photo(
        uid,
        IMG_PROFILE,
        caption=(
            f"👤 Профиль\n\n"
            f"🆔 ID: {uid}\n"
            f"⭐ Баланс: {get_balance(uid)}\n"
            f"👥 Рефералов: {ref_count}"
        )
    )

# ===== РЕФЕРАЛЫ =====
@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def refs(m):
    uid = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"

    cursor.execute("SELECT user_id FROM refs WHERE ref_id=?", (uid,))
    users = cursor.fetchall()

    text = f"👥 Твоя ссылка:\n{link}\n\n📊 Рефералы:\n"

    if not users:
        text += "❌ Нет"
    else:
        for u in users:
            text += f"👤 ID: {u[0]}\n"

    bot.send_message(uid, text)

# ===== ПОКУПКА =====
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(m):
    kb = types.InlineKeyboardMarkup()
    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_photo(m.chat.id, IMG_STARS, caption="💰 Выберите пакет:", reply_markup=kb)

# ===== ВЫБОР =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}"))

    bot.edit_message_caption(
        caption=f"{amount}⭐ = {price}₽",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ===== СБЕР =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(
        c.message.chat.id,
        f"💳 Карта: {CARD_NUMBER}\n📱 Телефон: {PHONE_NUMBER}\n\nСумма: {price}₽",
        reply_markup=kb
    )

# ===== ПРОВЕРКА =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(c):
    amount = c.data.split("_")[1]

    user = c.from_user
    username = f"@{user.username}" if user.username else "нет username"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{user.id}_{amount}"
    ))

    for admin in ADMIN_IDS:
        bot.send_message(
            admin,
            f"💰 Оплата\n\n👤 {username}\n🆔 {user.id}\n⭐ {amount}",
            reply_markup=kb
        )

    bot.send_message(user.id, "⏳ Ожидайте подтверждения")

# ===== ПОДТВЕРЖДЕНИЕ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(c):
    uid, amount = c.data.split("_")[1:]
    uid = int(uid)
    amount = int(amount)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Выдал", callback_data=f"done_{uid}_{amount}"))

    bot.edit_message_text(
        f"📦 Заказ\n\n👤 ID: {uid}\n⭐ {amount}\n\nНажми после выдачи",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

# ===== ВЫДАЛ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("done_"))
def done(c):
    uid, amount = c.data.split("_")[1:]
    uid = int(uid)
    amount = int(amount)

    bot.send_message(uid, f"✅ Вам выдано {amount} Telegram Stars!")

    ref = get_ref(uid)
    if ref:
        bonus = int(amount * 0.10)
        update_balance(ref, bonus)
        bot.send_message(ref, f"🎁 +{bonus}⭐ (10%)")

    bot.answer_callback_query(c.id, "Готово")

# ===== СТАРТ =====
bot.infinity_polling(skip_pending=True)