import telebot
from telebot import types
import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

ADMIN_IDS = [7315281700]

bot = telebot.TeleBot(TOKEN)

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

# --- РЕФЕРАЛКА ---
users = {}
REF_BONUS = 10

# --- МЕНЮ ---
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Купить звезды", "👤 Профиль")
    kb.add("👥 Рефералы")
    return kb

# --- СТАРТ ---
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "invited": 0,
            "ref_used": False
        }

    # реферал
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id and ref_id in users and not users[user_id]["ref_used"]:
                users[user_id]["ref_used"] = True
                users[ref_id]["balance"] += REF_BONUS
                users[ref_id]["invited"] += 1

                bot.send_message(ref_id, f"🎉 Новый реферал! +{REF_BONUS} ⭐")
        except:
            pass

    bot.send_photo(
        message.chat.id,
        IMG_WELCOME,
        caption=(
            "👋 <b>Добро пожаловать в Aulshop!</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"⭐ Баланс: <b>{users[user_id]['balance']}</b>\n\n"
            "Выберите действие 👇"
        ),
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# --- ПРОФИЛЬ ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    u = users[message.from_user.id]

    bot.send_photo(
        message.chat.id,
        IMG_PROFILE,
        caption=(
            "👤 <b>Профиль</b>\n\n"
            f"🆔 {message.from_user.id}\n"
            f"👤 @{message.from_user.username or 'нет'}\n"
            f"⭐ Баланс: <b>{u['balance']}</b>\n"
            f"👥 Рефералы: {u['invited']}"
        ),
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# --- РЕФЕРАЛЫ ---
@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def ref(message):
    user_id = message.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(
        message.chat.id,
        f"""
👥 <b>Реферальная система</b>

🔗 {link}

👥 Приглашено: {users[user_id]['invited']}
⭐ Баланс: {users[user_id]['balance']}

🎁 За друга: +{REF_BONUS} ⭐
""",
        parse_mode="HTML"
    )

# --- ВЫБОР ЗВЕЗД ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def choose(message):
    kb = types.InlineKeyboardMarkup()

    for s, p in prices.items():
        kb.add(types.InlineKeyboardButton(
            f"{s} ⭐ — {p} ₽",
            callback_data=f"buy_{s}"
        ))

    bot.send_photo(
        message.chat.id,
        IMG_STARS,
        caption="⭐ Выберите пакет",
        reply_markup=kb
    )

# --- ВЫБОР ОПЛАТЫ ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(call):
    amount = call.data.split("_")[1]
    rub = prices[amount]
    stars = rub * 2

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Сбер", callback_data=f"sber_{amount}"))
    kb.add(types.InlineKeyboardButton("💎 Crypto", callback_data=f"crypto_{amount}"))
    kb.add(types.InlineKeyboardButton(f"⭐ Купить за {stars}", callback_data=f"star_{amount}"))

    bot.edit_message_caption(
        caption=f"{amount} ⭐\n{rub} ₽ | {stars} ⭐",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )
    # --- ПОКУПКА ЗА ЗВЕЗДЫ ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("star_"))
def pay_star(call):
    user_id = call.from_user.id
    amount = call.data.split("_")[1]
    price = prices[amount] * 2

    if users[user_id]["balance"] < price:
        bot.answer_callback_query(call.id, "❌ Недостаточно звёзд")
        return

    users[user_id]["balance"] -= price

    bot.send_message(
        call.message.chat.id,
        f"✅ Куплено за ⭐\n{amount} придут в течение 5 минут"
    )

# --- СБЕР ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("sber_"))
def sber(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(
        call.message.chat.id,
        f"💳 Сбер\n\nСумма: {price} ₽\n\nПосле оплаты нажми кнопку",
        reply_markup=kb
    )

# --- CRYPTO ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def crypto(call):
    amount = call.data.split("_")[1]
    price = prices[amount]

    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}

    r = requests.post(url, headers=headers, json={
        "asset": "USDT",
        "amount": price / 100,
        "description": f"{amount} stars"
    }).json()

    if not r.get("ok"):
        bot.send_message(call.message.chat.id, "Ошибка оплаты")
        return

    pay_url = r["result"]["pay_url"]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Оплатить", url=pay_url))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_{amount}"))

    bot.send_message(call.message.chat.id, "💎 Оплата:", reply_markup=kb)

# --- ПРОВЕРКА ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(call):
    amount = call.data.split("_")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{call.from_user.id}_{amount}"
    ))

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"Оплата от @{call.from_user.username}", reply_markup=kb)

    bot.send_message(call.message.chat.id, "⏳ Ждите подтверждения")

# --- ПОДТВЕРЖДЕНИЕ ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(call):
    uid, amount = call.data.split("_")[1:]
    bot.send_message(int(uid), f"✅ Оплата подтверждена\n{amount} скоро придут")
    bot.answer_callback_query(call.id, "Готово")

# --- ЗАПУСК ---
bot.infinity_polling(skip_pending=True)
