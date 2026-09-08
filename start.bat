@echo off
chcp 65001 >nul
REM AI 智能客服 一键启动 (Windows)
cd /d "%~dp0"

REM ===== 自动选择 Python：优先项目自带 .venv，其次系统全局 Python =====
set PY=C:\Python314\python.exe
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

if not exist ".venv\Scripts\python.exe" (
  "%PY%" -c "import fastapi, gradio" 2>nul
  if errorlevel 1 (
    echo 首次运行：当前 Python 缺少依赖，创建虚拟环境并安装（约 1-3 分钟）...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    set PY=.venv\Scripts\python.exe
  )
)

echo 启动 API 服务 (端口 8000)...
start "cs-api" cmd /k %PY% api_server.py

echo 启动客服界面 (端口 7860)...
start "cs-ui" cmd /k %PY% ui.py

echo.
echo 等待服务启动...
timeout /t 8 /nobreak >nul
echo.
echo 聊天界面:  http://localhost:7860
echo API 文档:  http://localhost:8000/docs
echo 关闭服务: 直接关闭弹出的两个黑色窗口即可
pause
