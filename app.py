import telebot
import requests
import os
from telebot import types

# --- токены ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")  # токен ЮMoney

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

# --- меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 Профиль", "⭐ Купить звезды")
    markup.add("⚙️ Настройки")
    return markup

# --- старт ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать!",
        reply_markup=main_menu()
    )

# --- профиль ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    bot.send_message(
        message.chat.id,
        f"👤 ID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'нет'}",
        reply_markup=main_menu()
    )

# --- покупка ---
@bot.message_handler(func=lambda m: m.text == "⭐ Купить звезды")
def buy_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for stars, price in prices.items():
        markup.add(f"{stars} ⭐ — {price} ₽")

    markup.add("⬅️ Назад")

    bot.send_message(message.chat.id, "Выберите пакет:", reply_markup=markup)

# --- назад ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "Главное меню", reply_markup=main_menu())

# --- создание ссылки ЮMoney ---
def create_payment(amount, user_id):
    # ЮMoney quickpay (работает с картой и СБП)
    receiver = "4100111111111111"  # ❗ сюда свой номер кошелька

    url = "https://yoomoney.ru/quickpay/confirm.xml"

    params = {
        "receiver": receiver,
        "quickpay-form": "shop",
        "targets": f"Оплата {amount}₽ user {user_id}",
        "paymentType": "AC",  # карта (и СБП автоматически)
        "sum": amount,
        "label": str(user_id)
    }

    # формируем ссылку
    link = url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    return link

# --- обработка выбора пакета ---
@bot.message_handler(func=lambda m: True)
def process_buy(message):
    try:
        text = message.text.strip()

        if not text or not text.split()[0].isdigit():
            return

        amount = text.split()[0]

        if amount not in prices:
            return

        price = prices[amount]

        pay_url = create_payment(price, message.from_user.id)

        bot.send_message(
            message.chat.id,
            f"💳 Оплати здесь (карта / СБП):\n{pay_url}"
        )

        bot.send_message(
            ADMIN_ID,
            f"💰 Новый заказ {amount} ⭐ от @{message.from_user.username}"
        )

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "Ошибка")

# --- запуск ---
bot.infinity_polling()
