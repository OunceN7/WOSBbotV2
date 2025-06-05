import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatMemberStatus
from aiogram.utils.keyboard import ReplyKeyboardRemove
import asyncio
from datetime import datetime

# === НАСТРОЙКИ ===
import os
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 509766436
GROUP_ID = -1002400274681

# === НАСТРОЙКА БОТА ===
bot = Bot(token=TOKEN)
dp = Dispatcher()

# === ЛОГГИРОВАНИЕ ===
logging.basicConfig(level=logging.INFO)

# === БАЗА ДАННЫХ ===
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    nickname TEXT,
    join_date TEXT,
    in_group INTEGER
)
""")
conn.commit()

# === ПРОВЕРКА СОСТОИТ ЛИ В ГРУППЕ ===
async def check_membership(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(GROUP_ID, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

# === /start ===
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    in_group = await check_membership(user_id)

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        await message.answer("Вы уже зарегистрированы.")
        return

    await message.answer("Привет! Введи свой ник в игре:")
    dp.message.register(save_nickname, user_id=user_id, username=username, in_group=in_group)

# === СОХРАНЕНИЕ НИКА ===
async def save_nickname(message: Message, user_id: int, username: str, in_group: bool):
    nickname = message.text.strip()
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO users (user_id, username, nickname, join_date, in_group) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, nickname, join_date, int(in_group))
    )
    conn.commit()

    await message.answer(f"Спасибо, {nickname} зарегистрирован!", reply_markup=ReplyKeyboardRemove())

# === /список (только для админа) ===
@dp.message(Command("список"))
async def send_user_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT user_id, username, nickname, join_date, in_group FROM users")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Нет зарегистрированных пользователей.")
        return

    text = "👥 Зарегистрированные пользователи:\n"
    for row in rows:
        uid, uname, nick, date, ingrp = row
        text += f"- {nick} (@{uname}) — {date} — {'✅' if ingrp else '❌'}\n"
    await message.answer(text)

# === /рассылка (только для админа) ===
@dp.message(Command("рассылка"))
async def ask_broadcast_text(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Введите текст рассылки:")
    dp.message.register(do_broadcast)

async def do_broadcast(message: Message):
    text = message.text.strip()
    cursor.execute("SELECT user_id FROM users WHERE in_group = 1")
    users = cursor.fetchall()

    count = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            count += 1
        except:
            pass
    await message.answer(f"Рассылка отправлена {count} пользователям.")

# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())