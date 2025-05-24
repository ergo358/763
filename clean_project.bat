@echo off
REM Очистка всего окружения для Windows

cd /d "%~dp0"
if exist src\node_modules (
    rmdir /s /q src\node_modules
)
if exist src\build (
    rmdir /s /q src\build
)
if exist bot\venv (
    rmdir /s /q bot\venv
)
if exist bot\bot.db (
    del /q bot\bot.db
)
echo Проект очищен (node_modules, build, venv, bot.db удалены)
pause