import telebot
from telebot import types
import requests
import os
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

ADMIN_IDS = [7315281700]

bot = telebot.TeleBot(TOKEN)

# ================= БАЗА =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    ref INTEGER,
    banned INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= НАСТРОЙКИ =================
prices = {
    "25": 35,
    "50": 75,
    "100": 125
}

IMG = "https://imglink.cc/cdn/K3tbrvOvzl.jpg"

# ================= ФУНКЦИИ =================
def add_user(uid, ref=None):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, ref) VALUES (?, ?)", (uid, ref))
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

# ================= МЕНЮ =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить", "👤 Профиль")
    return kb

# ================= СТАРТ =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    add_user(uid)

    bot.send_photo(
        uid,
        IMG,
        caption=f"👋 Aulshop\n\n🆔 {uid}\n⭐ {get_balance(uid)}",
        reply_markup=menu()
    )

# ================= ПРОФИЛЬ =================
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = m.from_user.id

    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    bot.send_message(uid, f"🆔 {uid}\n⭐ Баланс: {get_balance(uid)}")

# ================= ПОКУПКА =================
@bot.message_handler(func=lambda m: m.text == "⭐ Купить")
def buy_menu(m):
    kb = types.InlineKeyboardMarkup()

    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_message(m.chat.id, "Выберите:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}"))
    kb.add(types.InlineKeyboardButton(f"⭐ Купить за {price}", callback_data=f"star_{amount}"))

    bot.edit_message_text(
        f"{amount}⭐ = {price}₽",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

# ================= ПОКУПКА ЗА ⭐ =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("star_"))
def pay_star(c):
    uid = c.from_user.id
    amount = c.data.split("_")[1]
    price = prices[amount]

    if get_balance(uid) < price:
        bot.answer_callback_query(c.id, "❌ Недостаточно")
        return

    update_balance(uid, -price)
    bot.send_message(uid, f"✅ Куплено {amount}⭐")

# ================= СБЕР =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(c.message.chat.id, f"Оплати {price}₽ и нажми кнопку", reply_markup=kb)

# ================= CRYPTO =================
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

        bot.send_message(c.message.chat.id, "Оплата:", reply_markup=kb)
    except:
        bot.send_message(c.message.chat.id, "Ошибка оплаты")

# ================= АДМИН =================
@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Выдать", "🚫 Бан")
    kb.add("✅ Разбан")

    bot.send_message(m.chat.id, "Админ панель", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Выдать")
def give(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    msg = bot.send_message(m.chat.id, "ID СУММА")
    bot.register_next_step_handler(msg, process_give)

def process_give(m):
    try:
        uid, amount = map(int, m.text.split())
        update_balance(uid, amount)
        bot.send_message(uid, f"🎁 +{amount}⭐")
    except:
        bot.send_message(m.chat.id, "Ошибка")

@bot.message_handler(func=lambda m: m.text == "🚫 Бан")
def ban(m):
    msg = bot.send_message(m.chat.id, "ID")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "🚫 Вы заблокированы")
    except:
        bot.send_message(m.chat.id, "Ошибка")

@bot.message_handler(func=lambda m: m.text == "✅ Разбан")
def unban(m):
    msg = bot.send_message(m.chat.id, "ID")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "✅ Разблокированы")
    except:
        bot.send_message(m.chat.id, "Ошибка")

# ================= СТАРТ БОТА =================
bot.infinity_polling(skip_pending=True)
