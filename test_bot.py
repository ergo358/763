import os
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot
import asyncio

async def test_token():
    token = os.getenv("API_TOKEN")
    if not token:
        print("Нет API_TOKEN")
        return False
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"TestBot username: @{me.username}")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("== Тест backend-бота ==")
    result = asyncio.run(test_token())
    if result:
        print("Backend тест пройден!")
        exit(0)
    else:
        print("Backend тест НЕ пройден!")
        exit(1)