import telebot
from telebot import types
import requests
import os
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")

ADMIN_IDS = [7315281700]

bot = telebot.TeleBot(TOKEN)

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

# ===== НА
