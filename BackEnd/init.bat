@echo off
chcp 65001 >nul
color 0A
title 智财云 - 智能财务分析系统

echo ==================================================
echo.
echo           欢迎使用 智财云 AI 财务分析系统
echo.
echo ==================================================
echo.

echo [1/3] 正在检查并安装必要的运行库 (第一次启动可能较慢)...
pip install -r requirements.txt -q
echo 运行库检查完毕！
echo.

echo [2/3] 正在启动后端与 AI 大脑服务...
:: 使用 start /b 在后台运行 python，不阻塞当前窗口
start /b python main.py
echo 服务正在启动，请稍候...

:: 等待 4 秒，确保 Python 服务完全启动
timeout /t 4 /nobreak >nul
echo.

echo [3/3] 正在打开浏览器...
start http://127.0.0.1:8000

echo.
echo ==================================================
echo ✅ 系统已成功运行！
echo ⚠️ 请不要关闭此黑色窗口，否则系统将停止运行。
echo ==================================================
pause