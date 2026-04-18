import telebot
from telebot import types
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7315281700]  # можно добавить второго админа

bot = telebot.TeleBot(TOKEN)

prices = {
    "25": 35,
    "50": 75,
    "100": 125,
    "150": 175,
    "200": 225,
    "300": 325
}

# --- картинки ---
IMG_WELCOME = "https://telegra.ph/file/7a0a1b9f5c7f6e4a8b9a1.jpg"
IMG_PROFILE = "https://telegra.ph/file/3c2d4e5f6a7b8c9d0e1f2.jpg"
IMG_STARS = "https://telegra.ph/file/5d6e7f8a9b0c1d2e3f4a5.jpg"

# --- меню ---
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Профиль", "⭐ Купить звезды")
    kb.add("⚙️ Настройки")
    return kb

# --- старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_photo(
        message.chat.id,
        IMG_WELCOME,
        caption="👋 Добро пожаловать!\nВыберите действие:",
        reply_markup=main_menu()
    )

# --- профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    bot.send_photo(
        message.chat.id,
        IMG_PROFILE,
        caption=f"👤 Профиль\n\nID: {message.from_user.id}\nUsername: @{message.from_user.username or 'нет'}",
        reply_markup=main_menu()
    )

# --- выбор звезд ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def stars(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for k, v in prices.items():
        kb.add(f"{k} ⭐ — {v} ₽")

    kb.add("⬅️ Назад")

    bot.send_photo(
        message.chat.id,
        IMG_STARS,
        caption="⭐ Выберите пакет:",
        reply_markup=kb
    )

# --- покупка ---
@bot.message_handler(func=lambda m: "⭐" in m.text)
def buy(message):
    amount = message.text.split("⭐")[0].strip()
    price = prices.get(amount)

    if not price:
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "💳 Оплатить",
        url=f"https://yoomoney.ru/to/4100119516144115?amount={price}"
    ))

    bot.send_message(
        message.chat.id,
        f"💰 К оплате: {price} ₽",
        reply_markup=kb
    )

    kb2 = types.InlineKeyboardMarkup()
    kb2.add(types.InlineKeyboardButton(
        "✅ Я оплатил",
        callback_data=f"check_{amount}"
    ))

    bot.send_message(message.chat.id, "После оплаты нажмите:", reply_markup=kb2)

# --- проверка ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(call):
    for admin in ADMIN_IDS:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"confirm_{call.from_user.id}"
        ))

        bot.send_message(
            admin,
            f"💰 Оплата от @{call.from_user.username}",
            reply_markup=kb
        )

    bot.send_message(call.message.chat.id, "⏳ Ожидайте подтверждение")

# --- подтверждение ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(call):
    user_id = int(call.data.split("_")[1])

    bot.send_message(
        user_id,
        "✅ Оплата подтверждена!\n📦 Товар придет в течение 5 минут"
    )

# --- назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "🔙 Меню", reply_markup=main_menu())

bot.polling(none_stop=True)
