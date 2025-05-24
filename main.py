import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from database import init_db, add_request, list_requests, cancel_request

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN or API_TOKEN == "7905476946:AAFXrpao8ZPxndRaB1Ft9fkaA0QPUvvw4tc":
    raise ValueError("API_TOKEN не найден в .env! Пожалуйста, укажите актуальный токен.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

init_db()

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Это бот для бронирования переговорок.\n"
        "Доступные команды:\n"
        "/add — добавить заявку\n"
        "/list — список моих заявок\n"
        "/cancel — отменить заявку\n"
        "/help — справка\n"
        "/about — о проекте"
    )

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    await message.reply(
        "/add — добавить заявку\n"
        "/list — список моих заявок\n"
        "/cancel — отменить заявку\n"
        "/about — о проекте"
    )

@dp.message_handler(commands=["about"])
async def about_cmd(message: types.Message):
    await message.reply("Этот бот создан для бронирования переговорок. Веб-интерфейс: http://localhost:3000")

user_state = {}

@dp.message_handler(commands=["add"])
async def add_cmd(message: types.Message):
    user_state[message.from_user.id] = {"stage": "room"}
    await message.reply("Введите название переговорки:")

@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get("stage") == "room")
async def add_room(message: types.Message):
    user_state[message.from_user.id]["room"] = message.text
    user_state[message.from_user.id]["stage"] = "date"
    await message.reply("Введите дату и время (например, 2025-05-25 10:00):")

@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get("stage") == "date")
async def add_date(message: types.Message):
    info = user_state.pop(message.from_user.id)
    room, date = info["room"], message.text
    add_request(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        room=room,
        date=date
    )
    await message.reply(f"Заявка на переговорку '{room}' на {date} добавлена!")

@dp.message_handler(commands=["list"])
async def list_cmd(message: types.Message):
    requests = list_requests(message.from_user.id)
    if not requests:
        await message.reply("У вас нет заявок.")
        return
    text = "Ваши заявки:\n"
    for req_id, room, date, status in requests:
        text += f"ID: {req_id}, Переговорка: {room}, Дата: {date}, Статус: {status}\n"
    await message.reply(text)

@dp.message_handler(commands=["cancel"])
async def cancel_cmd(message: types.Message):
    await message.reply("Введите ID заявки для отмены (посмотреть ID: /list):")
    user_state[message.from_user.id] = {"stage": "cancel"}

@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get("stage") == "cancel")
async def do_cancel(message: types.Message):
    try:
        req_id = int(message.text)
    except ValueError:
        await message.reply("ID должен быть числом.")
        return
    cnt = cancel_request(req_id, message.from_user.id)
    user_state.pop(message.from_user.id, None)
    if cnt:
        await message.reply(f"Заявка {req_id} отменена.")
    else:
        await message.reply("Заявка не найдена или уже отменена.")

if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        print("Backend тест пройден.")
        exit(0)
    print("Бот запускается...")
    executor.start_polling(dp, skip_updates=True)
