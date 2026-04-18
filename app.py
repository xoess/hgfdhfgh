import telebot
from telebot import types
import os

TOKEN = os.getenv("BOT_TOKEN")
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

# --- картинки ---
IMG_WELCOME = "AgACAgIAAxkBAAFHfEJp414ILgFPZIHifeOyuZ91oeZisAACQBRrGwUTIEvx4itiwJkrVgEAAwIAA3MAAzsE"
IMG_PROFILE = "AgACAgIAAxkBAAFHfEhp414mwl9xrct8OAe7IlWYYm765AACQhRrGwUTIEuE_EUM3sPNPQEAAwIAA20AAzsE"
IMG_STARS = "AgACAgIAAxkBAAFHfExp4143555vDfUCWXuQYf6ivlH8qAACQxRrGwUTIEvn6IWhnnNfXgEAAwIAA3kAAzsE"

# --- главное меню ---
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
        caption="👋 Добро пожаловать в AulShop!\nВыберите действие:",
        reply_markup=main_menu()
    )

# --- профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    text = f"""
👤 Ваш профиль:

🆔 ID: {message.from_user.id}
📛 Username: @{message.from_user.username if message.from_user.username else 'нет'}
"""

    bot.send_photo(
        message.chat.id,
        IMG_PROFILE,
        caption=text,
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

# --- обработка покупки ---
@bot.message_handler(func=lambda m: "⭐" in m.text)
def buy(message):
    try:
        amount = message.text.split("⭐")[0].strip()
        price = prices.get(amount)

        if not price:
            return

        # кнопка оплаты
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "💳 Оплатить (ЮMoney)",
            url=f"https://yoomoney.ru/to/4100119516144115?amount={price}"
        ))

        bot.send_message(
            message.chat.id,
            f"💰 К оплате: {price} ₽\nВыберите способ:",
            reply_markup=kb
        )

        # кнопка "я оплатил"
        kb2 = types.InlineKeyboardMarkup()
        kb2.add(types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data=f"check_{amount}"
        ))

        bot.send_message(
            message.chat.id,
            "После оплаты нажмите кнопку:",
            reply_markup=kb2
        )

    except:
        bot.send_message(message.chat.id, "❌ Ошибка")

# --- проверка оплаты ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check(call):
    amount = call.data.split("_")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"confirm_{call.from_user.id}_{amount}"
    ))

    bot.send_message(
        ADMIN_ID,
        f"💰 Заявка на оплату\n\n👤 @{call.from_user.username}\n⭐ {amount}",
        reply_markup=kb
    )

    bot.send_message(call.message.chat.id, "⏳ Ожидаем подтверждение...")

# --- подтверждение админом ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm(call):
    user_id = int(call.data.split("_")[1])
    amount = call.data.split("_")[2]

    bot.send_message(
        user_id,
        f"✅ Оплата подтверждена!\n\n⭐ {amount} будет отправлено в течение 5 минут"
    )

    bot.answer_callback_query(call.id, "Подтверждено")

# --- назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "🔙 Главное меню", reply_markup=main_menu())

bot.polling()
