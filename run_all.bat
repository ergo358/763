@echo off
chcp 65001
setlocal
cd /d "%~dp0"

REM === [1. Backend setup] ===
echo === [Backend] Creating and activating venv...
cd bot
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate

echo === [Backend] Installing dependencies...
if not exist requirements.txt (
    echo [ERROR] bot\requirements.txt not found!
    pause
    exit /b 1
)
pip install -r requirements.txt

REM === [2. Backend API start (background)] ===
echo === [Backend] Starting FastAPI (api.py) at http://localhost:8000 ...
start "" cmd /c "uvicorn api:app --host 127.0.0.1 --port 8000 > api_log.txt 2>&1"
timeout /t 5 >nul

REM === [3. Backend tests] ===
echo === [Backend] Syntax check *.py...
for %%f in (*.py) do (
    python -m py_compile "%%f"
    if errorlevel 1 (
        echo [ERROR] Python syntax: errors found in %%f!
        pause
        exit /b 1
    )
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
start "" cmd /c "call venv\Scripts\activate && python main.py > bot_log.txt 2>&1"

deactivate
cd ..

REM === [4. Frontend setup] ===
echo === [Frontend] Installing dependencies...
cd src
if not exist node_modules (
    npm install
)

REM === [5. Frontend build] ===
echo === [Frontend] Building React app...
npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build: errors found!
    pause
    exit /b 1
)

REM === [6. Frontend tests] ===
echo === [Frontend] Running React tests...
npm test -- --watchAll=false
if errorlevel 1 (
    echo [ERROR] Frontend tests: errors found!
    pause
    exit /b 1
)

REM === [7. Start frontend and open browser] ===
echo === [Frontend] Starting local server...
start "" cmd /c "npx serve -s build -l 3000 > frontend_log.txt 2>&1"
timeout /t 3 >nul
start http://localhost:3000

cd ..

echo.
echo === ALL OK! Project is running and opened in browser.
echo === Окно НЕ будет закрыто автоматически.
echo === Для остановки backend и frontend просто закрой это окно вручную.
echo.
pause