@echo off
cd /d "%~dp0"
if not exist .venv\ready (
  echo First run: setting up Friday...
  python -m venv .venv || (echo Install Python 3.10+ from python.org first and tick "Add python.exe to PATH". & pause & exit /b 1)
  .venv\Scripts\python -m pip install -q -r requirements.txt || (echo Install failed. Check your internet. & pause & exit /b 1)
  echo ok> .venv\ready
)
if not exist .env (
  copy .env.example .env >nul
  echo Paste your API key into the .env file that just opened, save it, then run start.bat again.
  notepad .env
  exit /b 0
)
start "" http://localhost:8000
.venv\Scripts\python server.py
pause
