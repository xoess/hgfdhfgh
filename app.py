import telebot
from telebot import types
import sqlite3
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# 💥 ФИКС 409 ОШИБКИ
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
    "25": 35,
    "50": 75,
    "100": 125,
    "150": 175,
    "200": 225
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
def main_menu():
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
        reply_markup=main_menu()
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
        reply_markup=main_menu()
    )

# ===== ПОКУПКА =====
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(m):
    kb = types.InlineKeyboardMarkup()

    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_photo(m.chat.id, IMG_STARS, caption="💰 Выберите пакет:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"⭐ Купить за {price}", callback_data=f"pay_{amount}"))

    bot.edit_message_caption(
        caption=f"{amount}⭐ = {price}₽",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay(c):
    uid = c.from_user.id
    amount = c.data.split("_")[1]
    price = prices[amount]

    bot.send_message(uid, f"💳 Переведи {price}₽ на Сбер\n\nПосле оплаты нажми /check")

# ===== ПРОВЕРКА =====
@bot.message_handler(commands=['check'])
def check(m):
    uid = m.from_user.id

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{uid}"))

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"💰 Оплата от {uid}", reply_markup=kb)

    bot.send_message(uid, "⏳ Ожидай подтверждения")

# ===== ПОДТВЕРЖДЕНИЕ =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(c):
    uid = int(c.data.split("_")[1])

    update_balance(uid, 100)

    bot.send_message(uid, "✅ Оплата подтверждена\n⭐ Зачислено!")
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
