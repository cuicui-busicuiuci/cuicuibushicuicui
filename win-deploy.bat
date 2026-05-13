@echo off
chcp 65001 >nul
title A股量化投研系统 - 一键部署

echo ============================================
echo   A股量化投研系统 - Windows一键部署
echo ============================================
echo.

:: 安装依赖 (winget 是 Win11 自带的)
echo [1/5] 安装基础工具...
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS --accept-package-agreements --silent 2>nul
echo 已完成 (如有报错说明已安装，忽略即可)

:: 刷新 PATH
set PATH=%ProgramFiles%\Git\bin;%ProgramFiles%\Git\cmd;%PATH%
set PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%
set PATH=%ProgramFiles%\nodejs;%PATH%

:: 克隆项目
echo [2/5] 克隆项目...
git clone https://github.com/cuicui-busicuiuci/cuicuibushicuicui.git %USERPROFILE%\stock-ai-platform
cd /d %USERPROFILE%\stock-ai-platform

:: 后端
echo [3/5] 安装后端依赖...
cd backend
pip install -r requirements.txt
cd ..

:: 前端
echo [4/5] 安装前端依赖...
cd frontend
call npm install
cd ..

:: 启动
echo [5/5] 启动服务...
cd backend
start "Stock-Backend-8017" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8017"
cd ..

cd frontend
start "Stock-Frontend-3000" cmd /c "npm run dev"
cd ..

:: 防火墙
netsh advfirewall firewall add rule name="Stock-Backend" dir=in action=allow protocol=TCP localport=8017 >nul 2>&1
netsh advfirewall firewall add rule name="Stock-Frontend" dir=in action=allow protocol=TCP localport=3000 >nul 2>&1

echo.
echo ============================================
echo   部署完成！
echo   前端: http://localhost:3000
echo   API:  http://localhost:8017/docs
echo ============================================
echo.
echo 按任意键退出...
pause >nul
