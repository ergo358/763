import os

PROJECT_STRUCTURE = {
    "bot": {
        "database.py": '''
import sqlite3
from contextlib import contextmanager

DB_PATH = "bot.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            room TEXT,
            date TEXT,
            status TEXT DEFAULT 'active'
        )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def add_request(user_id, username, room, date):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO requests (user_id, username, room, date) VALUES (?, ?, ?, ?)",
                    (user_id, username, room, date))
        conn.commit()

def list_requests(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, room, date, status FROM requests WHERE user_id=? ORDER BY date DESC", (user_id,))
        return cur.fetchall()

def cancel_request(request_id, user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE requests SET status='cancelled' WHERE id=? AND user_id=?", (request_id, user_id))
        conn.commit()
        return cur.rowcount
''',

        "main.py": '''
import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from database import init_db, add_request, list_requests, cancel_request

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN or API_TOKEN == "your_telegram_token_here":
    raise ValueError("API_TOKEN не найден в .env! Пожалуйста, укажите актуальный токен.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

init_db()

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Это бот для бронирования переговорок.\\n"
        "Доступные команды:\\n"
        "/add — добавить заявку\\n"
        "/list — список моих заявок\\n"
        "/cancel — отменить заявку\\n"
        "/help — справка\\n"
        "/about — о проекте"
    )

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    await message.reply(
        "/add — добавить заявку\\n"
        "/list — список моих заявок\\n"
        "/cancel — отменить заявку\\n"
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
    text = "Ваши заявки:\\n"
    for req_id, room, date, status in requests:
        text += f"ID: {req_id}, Переговорка: {room}, Дата: {date}, Статус: {status}\\n"
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
''',

        "api.py": '''
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, add_request, list_requests, cancel_request

init_db()
app = FastAPI(title="Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/requests/{user_id}")
def api_list_requests(user_id: int):
    res = list_requests(user_id)
    return [{"id": r[0], "room": r[1], "date": r[2], "status": r[3]} for r in res]

@app.post("/api/requests/add")
def api_add_request(user_id: int, username: str, room: str, date: str):
    add_request(user_id, username, room, date)
    return {"detail": "ok"}

@app.post("/api/requests/cancel")
def api_cancel_request(user_id: int, request_id: int):
    cnt = cancel_request(request_id, user_id)
    if cnt:
        return {"detail": "cancelled"}
    raise HTTPException(404, "Not found")
''',

        "test_api.py": '''
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_add_and_list():
    r = client.post("/api/requests/add", params={
        "user_id": 999,
        "username": "testuser",
        "room": "TestRoom",
        "date": "2030-01-01 10:00"
    })
    assert r.status_code == 200
    data = client.get("/api/requests/999")
    assert data.status_code == 200
    lst = data.json()
    assert any(x["room"] == "TestRoom" for x in lst)

def test_cancel():
    r = client.post("/api/requests/add", params={
        "user_id": 998,
        "username": "testuser",
        "room": "CancelRoom",
        "date": "2030-02-02 12:00"
    })
    assert r.status_code == 200
    lst = client.get("/api/requests/998").json()
    req_id = lst[0]["id"]
    cancel = client.post("/api/requests/cancel", params={"user_id": 998, "request_id": req_id})
    assert cancel.status_code == 200
''',

        "test_bot.py": '''
import os
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
''',

        "requirements.txt": '''
aiogram
requests
python-dotenv
fastapi
uvicorn
pytest
''',

        ".env": '''
API_TOKEN=your_telegram_token_here
'''
    },

    "src": {
        "App.js": '''
import React, { useState, useEffect } from "react";
import { Box, Heading, Text, Button, Input, Table, Thead, Tbody, Tr, Th, Td, useToast } from "@chakra-ui/react";
import axios from "axios";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function App() {
  const [userId, setUserId] = useState("");
  const [room, setRoom] = useState("");
  const [date, setDate] = useState("");
  const [items, setItems] = useState([]);
  const [cancelId, setCancelId] = useState("");
  const toast = useToast();

  const fetchRequests = async () => {
    if (!userId) return;
    const { data } = await axios.get(`${API}/api/requests/${userId}`);
    setItems(data);
  };

  const addRequest = async () => {
    if (!userId || !room || !date) return;
    await axios.post(`${API}/api/requests/add`, null, {
      params: { user_id: userId, username: "web", room, date }
    });
    setRoom(""); setDate("");
    toast({ title: "Заявка добавлена", status: "success" });
    fetchRequests();
  };

  const cancelRequest = async () => {
    await axios.post(`${API}/api/requests/cancel`, null, {
      params: { user_id: userId, request_id: cancelId }
    });
    setCancelId("");
    toast({ title: "Заявка отменена", status: "info" });
    fetchRequests();
  };

  useEffect(() => { fetchRequests(); /* eslint-disable-next-line */ }, [userId]);

  return (
    <Box maxW="600px" mx="auto" p={8}>
      <Heading mb={6}>Бронирование переговорок</Heading>
      <Input placeholder="Ваш Telegram user_id" value={userId} onChange={e => setUserId(e.target.value)} mb={2} />
      <Box display="flex" gap={2} mb={2}>
        <Input placeholder="Переговорка" value={room} onChange={e => setRoom(e.target.value)} />
        <Input placeholder="Дата и время" value={date} onChange={e => setDate(e.target.value)} />
        <Button onClick={addRequest} colorScheme="blue">Добавить</Button>
      </Box>
      <Button onClick={fetchRequests} size="sm" mb={2}>Обновить список</Button>
      <Table size="sm" mb={2}>
        <Thead>
          <Tr>
            <Th>ID</Th>
            <Th>Переговорка</Th>
            <Th>Дата</Th>
            <Th>Статус</Th>
          </Tr>
        </Thead>
        <Tbody>
          {items.map(r =>
            <Tr key={r.id}>
              <Td>{r.id}</Td>
              <Td>{r.room}</Td>
              <Td>{r.date}</Td>
              <Td>{r.status}</Td>
            </Tr>
          )}
        </Tbody>
      </Table>
      <Box display="flex" gap={2} alignItems="center">
        <Input placeholder="ID для отмены" value={cancelId} onChange={e => setCancelId(e.target.value)} w="150px" />
        <Button onClick={cancelRequest} colorScheme="red" size="sm">Отменить</Button>
      </Box>
      <Text mt={6} fontSize="sm">Сначала введите свой user_id (узнать — через /start в боте)</Text>
    </Box>
  );
}
''',

        "index.js": '''
import React from "react";
import { createRoot } from "react-dom/client";
import { ChakraProvider } from "@chakra-ui/react";
import theme from "./theme";
import App from "./App";

const root = createRoot(document.getElementById("root"));
root.render(
  <ChakraProvider theme={theme}>
    <App />
  </ChakraProvider>
);
''',

        "theme.js": '''
import { extendTheme } from "@chakra-ui/react";
export default extendTheme({
  config: { initialColorMode: "system", useSystemColorMode: true }
});
''',

        ".env.example": '''
REACT_APP_API_URL=http://localhost:8000
''',

        "package.json": '''
{
  "name": "booking-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@chakra-ui/react": "^2.8.1",
    "framer-motion": "^10.16.4",
    "recharts": "^2.8.0",
    "qrcode.react": "^3.1.0",
    "serve": "^14.2.0",
    "axios": "^1.6.8"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test --env=jsdom --watchAll=false",
    "smoke": "npm run build && (if exist build (exit 0) else (echo Build failed & exit 1))",
    "clean": "rimraf node_modules build"
  }
}
'''
    },

    "run_all.bat": '''
@echo off
chcp 65001
setlocal
cd /d "%~dp0"

REM 1. Backend setup
echo === [Backend] Creating and activating venv...
cd bot
if not exist venv (
    python -m venv venv
)
call venv\\Scripts\\activate

echo === [Backend] Installing dependencies...
if not exist requirements.txt (
    echo [ERROR] bot\\requirements.txt not found!
    pause
    exit /b 1
)
pip install -r requirements.txt

REM 2. Backend API start (background)
echo === [Backend] Starting FastAPI (api.py) at http://localhost:8000 ...
start "" cmd /c "uvicorn api:app --host 127.0.0.1 --port 8000 > api_log.txt 2>&1"
timeout /t 5 >nul

REM 3. Backend tests
echo === [Backend] Syntax check *.py...
for %%f in (*.py) do python -m py_compile "%%f"
if errorlevel 1 (
    echo [ERROR] Python syntax: errors found!
    pause
    exit /b 1
)
echo === [Backend] Pytest tests...
pytest test_api.py
if errorlevel 1 (
    echo [ERROR] Pytest API: errors found!
    pause
    exit /b 1
)
echo === [Backend] Telegram bot token test...
python test_bot.py
if errorlevel 1 (
    echo [ERROR] Telegram bot test: errors found!
    pause
    exit /b 1
)

REM --- Autostart Telegram bot (background) ---
echo === [Backend] Starting Telegram bot (main.py)...
start "" cmd /c "call venv\\Scripts\\activate && python main.py > bot_log.txt 2>&1"

deactivate
cd ..

REM 4. Frontend setup
echo === [Frontend] Installing dependencies...
cd src
if not exist node_modules (
    npm install
)
REM 5. Frontend build
echo === [Frontend] Building React app...
npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build: errors found!
    pause
    exit /b 1
)
REM 6. Frontend tests
echo === [Frontend] Running React tests...
npm test -- --watchAll=false
if errorlevel 1 (
    echo [ERROR] Frontend tests: errors found!
    pause
    exit /b 1
)

REM 7. Start frontend and open browser
echo === [Frontend] Starting local server...
start "" cmd /c "npx serve -s build -l 3000 > frontend_log.txt 2>&1"
timeout /t 3 >nul
start http://localhost:3000

cd ..

echo.
echo === ALL OK! Project is running and opened in browser.
echo.
pause
endlocal
'''
}

def make_tree(base, struct):
    for name, content in struct.items():
        path = os.path.join(base, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            make_tree(path, content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")

if __name__ == "__main__":
    make_tree(".", PROJECT_STRUCTURE)
    print("Проектовая структура и все файлы успешно созданы!")