import telebot
from telebot import types
import requests
import os
import sqlite3
import shutil
import threading
import time

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

ADMIN_IDS = [7315281700]

bot = telebot.TeleBot(TOKEN)

# ================= БАЗА =================
DB_NAME = "bot.db"
BACKUP_NAME = "backup.db"

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    invited INTEGER DEFAULT 0,
    ref INTEGER,
    banned INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------- BACKUP ----------
def backup_db():
    while True:
        try:
            shutil.copy(DB_NAME, BACKUP_NAME)
        except:
            pass
        time.sleep(60)

threading.Thread(target=backup_db, daemon=True).start()

# ================= ЛОГИКА =================

prices = {
    "25": 35,
    "50": 75,
    "100": 125,
    "150": 175,
    "200": 225,
    "300": 325
}

IMG_WELCOME = "https://imglink.cc/cdn/K3tbrvOvzl.jpg"
IMG_PROFILE = "https://imglink.cc/cdn/OZmDy2H4iI.jpg"
IMG_STARS   = "https://imglink.cc/cdn/_RxgFRvwh9.jpg"

REF_PERCENT = 10

# ---------- DB ----------
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

# ---------- РЕФ ----------
def give_ref_bonus(uid, amount):
    cursor.execute("SELECT ref FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()

    if not r or not r[0]:
        return

    ref_id = r[0]
    bonus = int(amount * REF_PERCENT / 100)

    update_balance(ref_id, bonus)

    try:
        bot.send_message(ref_id, f"💸 +{bonus} ⭐ (реферал)")
    except:
        pass

# ---------- МЕНЮ ----------
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить звезды", "👤 Профиль")
    kb.add("👥 Рефералы")
    return kb

# ================= USER =================

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id

    if is_banned(uid):
        return bot.send_message(uid, "🚫 Вы заблокированы")

    args = m.text.split()
    ref = None

    if len(args) > 1:
        try:
            ref = int(args[1])
        except:
            pass

    add_user(uid, ref)

    bot.send_photo(
        uid,
        IMG_WELCOME,
        caption=f"👋 Aulshop\n\n🆔 {uid}\n⭐ {get_balance(uid)}",
        reply_markup=menu()
    )

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = m.from_user.id

    if is_banned(uid):
        return bot.send_message(uid, "🚫 Вы заблокированы")

    bot.send_photo(
        uid,
        IMG_PROFILE,
        caption=f"🆔 {uid}\n⭐ {get_balance(uid)}",
        reply_markup=menu()
    )

@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def refs(m):
    uid = m.from_user.id

    if is_banned(uid):
        return bot.send_message(uid, "🚫 Вы заблокированы")

    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(uid, f"🔗 {link}\n💸 10% с покупок")

# ---------- ПОКУПКА ----------
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(m):
    uid = m.from_user.id

    if is_banned(uid):
        return bot.send_message(uid, "🚫 Вы заблокированы")

    kb = types.InlineKeyboardMarkup()
    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(f"{s}⭐ — {p}₽", callback_data=f"buy_{s}"))

    bot.send_photo(uid, IMG_STARS, caption="Выберите пакет", reply_markup=kb)
    @bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}"))
    kb.add(types.InlineKeyboardButton(f"⭐ Купить за {price}", callback_data=f"star_{amount}"))

    bot.edit_message_caption(
        caption=f"{amount}⭐ = {price}₽",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ---------- ЗА ⭐ ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("star_"))
def pay_star(c):
    uid = c.from_user.id
    amount = c.data.split("_")[1]
    price = prices[amount]

    if get_balance(uid) < price:
        return bot.answer_callback_query(c.id, "❌ Недостаточно")

    update_balance(uid, -price)
    give_ref_bonus(uid, price)

    bot.send_message(uid, f"✅ Куплено {amount}⭐")

# ---------- СБЕР ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(c):
    amount = c.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(c.message.chat.id, f"💳 Сбер\nСумма: {price}₽", reply_markup=kb)

# ---------- CRYPTO ----------
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

        bot.send_message(c.message.chat.id, "Оплата", reply_markup=kb)
    except:
        bot.send_message(c.message.chat.id, "❌ Ошибка оплаты")

# ---------- ПРОВЕРКА ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(c):
    amount = c.data.split("_")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{c.from_user.id}_{amount}"
    ))

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"Оплата от {c.from_user.id}", reply_markup=kb)

    bot.send_message(c.from_user.id, "⏳ Ожидайте")

# ---------- ПОДТВЕРЖДЕНИЕ ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(c):
    uid, amount = c.data.split("_")[1:]
    price = prices[amount]

    give_ref_bonus(int(uid), price)

    bot.send_message(uid, "✅ Подтверждено")
    bot.answer_callback_query(c.id, "OK")

# ================= ADMIN =================

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

    msg = bot.send_message(m.chat.id, "Введите: ID СУММА")
    bot.register_next_step_handler(msg, process_give)

def process_give(m):
    try:
        uid, amount = map(int, m.text.split())
        update_balance(uid, amount)
        bot.send_message(uid, f"🎁 +{amount}⭐")
        bot.send_message(m.chat.id, "✅ Готово")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

@bot.message_handler(func=lambda m: m.text == "🚫 Бан")
def ban(m):
    if m.from_user.id not in ADMIN_IDS:
        return
        msg = bot.send_message(m.chat.id, "Введите ID")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "🚫 Вы заблокированы")
        bot.send_message(m.chat.id, "✅ Заблокирован")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

@bot.message_handler(func=lambda m: m.text == "✅ Разбан")
def unban(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    msg = bot.send_message(m.chat.id, "Введите ID")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(m):
    try:
        uid = int(m.text)
        cursor.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "✅ Разблокированы")
        bot.send_message(m.chat.id, "✅ Готово")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

# ================= START =================
bot.infinity_polling(skip_pending=True)
