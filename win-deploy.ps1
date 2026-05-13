Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  A股量化投研系统 - 一键部署" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# 1. 安装依赖
Write-Host "[1/5] 安装 Git / Python / Node.js..." -ForegroundColor Yellow
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS --accept-package-agreements --silent 2>$null
Write-Host "  完成 (已安装的会跳过)" -ForegroundColor Green

# 刷新 PATH
$env:Path = "C:\Program Files\Git\bin;C:\Program Files\Git\cmd;$env:Path"
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:Path"
$env:Path = "C:\Program Files\nodejs;$env:Path"

# 2. 克隆项目
Write-Host "[2/5] 克隆项目..." -ForegroundColor Yellow
$projectDir = "$env:USERPROFILE\stock-ai-platform"
if (Test-Path $projectDir) { Remove-Item $projectDir -Recurse -Force }
git clone https://github.com/cuicui-busicuiuci/cuicuibushicuicui.git $projectDir
Set-Location $projectDir
Write-Host "  完成" -ForegroundColor Green

# 3. 后端依赖
Write-Host "[3/5] 安装后端依赖..." -ForegroundColor Yellow
Set-Location "$projectDir\backend"
pip install -r requirements.txt
Write-Host "  完成" -ForegroundColor Green

# 4. 前端依赖
Write-Host "[4/5] 安装前端依赖..." -ForegroundColor Yellow
Set-Location "$projectDir\frontend"
npm install
Write-Host "  完成" -ForegroundColor Green

# 5. 启动服务
Write-Host "[5/5] 启动服务..." -ForegroundColor Yellow

Start-Process cmd -ArgumentList "/c", "title Stock-Backend-8017 && cd /d $projectDir\backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8017"
Start-Sleep -Seconds 2
Start-Process cmd -ArgumentList "/c", "title Stock-Frontend-3000 && cd /d $projectDir\frontend && npm run dev"

# 防火墙
New-NetFirewallRule -DisplayName "Stock-Backend" -Direction Inbound -LocalPort 8017 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "Stock-Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "  前端: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API : http://localhost:8017/docs" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车退出"
