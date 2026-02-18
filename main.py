import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

API_TOKEN = "8368307123:AAFcIaT0sGIx9qCqP0K2o0oTXATUcxGEXas"
ADMIN_IDS = {5207844420}  # telegram_id админов

logging.basicConfig(level=logging.INFO)

# --- DB ---
conn = sqlite3.connect("users.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    internal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE
)
""")
conn.commit()


def get_or_create_user(telegram_id: int) -> int:
    cur.execute(
        "SELECT internal_id FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        "INSERT INTO users (telegram_id) VALUES (?)",
        (telegram_id,)
    )
    conn.commit()
    return cur.lastrowid


def get_telegram_id(internal_id: int) -> int | None:
    cur.execute(
        "SELECT telegram_id FROM users WHERE internal_id = ?",
        (internal_id,)
    )
    row = cur.fetchone()
    return row[0] if row else None


bot = Bot(API_TOKEN)
dp = Dispatcher()


# --- START ---
@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Админ-панель активна.")
    else:
        await message.answer("Напишите сообщение, оно будет передано админу.")


# --- USER -> ADMIN ---
@dp.message(F.from_user.id.not_in(ADMIN_IDS))
async def user_message(message: Message):
    internal_id = get_or_create_user(message.from_user.id)

    text = f"#ID: {internal_id}\n{message.text}"

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, text)


# --- ADMIN -> USER ---
@dp.message(F.from_user.id.in_(ADMIN_IDS))
async def admin_message(message: Message):
    # 1. Ответ через reply
    if message.reply_to_message and message.reply_to_message.text:
        header = message.reply_to_message.text.split("\n", 1)[0]
        if header.startswith("#ID:"):
            try:
                internal_id = int(header.replace("#ID:", "").strip())
                telegram_id = get_telegram_id(internal_id)
                if not telegram_id:
                    await message.reply("❌ ID не найден")
                    return

                await bot.send_message(telegram_id, message.text)
                return
            except ValueError:
                pass

    # 2. Ответ через ID в тексте
    if not message.text:
        return

    lines = message.text.split("\n", 1)
    if len(lines) < 2:
        await message.reply("❌ Формат:\nID\nТекст")
        return

    try:
        internal_id = int(lines[0].strip())
    except ValueError:
        await message.reply("❌ Некорректный ID")
        return

    telegram_id = get_telegram_id(internal_id)
    if not telegram_id:
        await message.reply("❌ ID не найден")
        return

    await bot.send_message(telegram_id, lines[1])


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())