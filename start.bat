@echo off
cd /d "%~dp0"

REM backend/ 是业务代码、frontend/ 是界面层，两边都要能被 import
set PYTHONPATH=%CD%\backend;%CD%\frontend

REM ===== pick python: prefer project .venv, fallback to system python =====
set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
  echo First run: creating venv and installing dependencies...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)

echo.
echo Starting AI Customer Service (single port)...
echo   UI : http://127.0.0.1:8000/
echo   API: http://127.0.0.1:8000/docs
echo.
echo Close this window to stop the service.
echo.
start "" http://127.0.0.1:8000/
"%PY%" backend\api_server.py
