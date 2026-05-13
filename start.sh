#!/bin/bash
# A股量化投研系统 — 一键启动
# 用法: bash start.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
CLOUDFLARED="$ROOT/../cloudflared.exe"

echo "=== A股量化投研系统 启动中 ==="

# 1. 后端
echo "[1/3] 启动后端 (8017)..."
cd "$ROOT/backend"
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8017 > /tmp/stock_backend.log 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 2. 前端
echo "[2/3] 启动前端 (3000)..."
cd "$ROOT/frontend"
nohup npm run dev > /tmp/stock_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

# 3. 等待服务就绪
echo "[3/3] 等待服务就绪..."
sleep 5

# 健康检查
if curl -s http://localhost:8017/api/system/health > /dev/null 2>&1; then
    echo "  ✓ 后端正常"
else
    echo "  ✗ 后端启动失败，查看 /tmp/stock_backend.log"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✓ 前端正常"
else
    echo "  ✗ 前端启动中，稍等片刻..."
fi

# 4. Cloudflare Tunnel
if [ -f "$CLOUDFLARED" ]; then
    echo ""
    echo "=== 启动外网 Tunnel ==="
    nohup "$CLOUDFLARED" tunnel --url http://localhost:8017 > /tmp/stock_tunnel_b.log 2>&1 &
    nohup "$CLOUDFLARED" tunnel --url http://localhost:3000 > /tmp/stock_tunnel_f.log 2>&1 &
    sleep 5
    B_URL=$(grep -o "https://[^ ]*trycloudflare.com" /tmp/stock_tunnel_b.log | tail -1)
    F_URL=$(grep -o "https://[^ ]*trycloudflare.com" /tmp/stock_tunnel_f.log | tail -1)
    echo "  后端API: $B_URL"
    echo "  前端页面: $F_URL"
fi

echo ""
echo "=== 系统已启动 ==="
echo "  本地: http://localhost:3000"
echo "  API:  http://localhost:8017/docs"
echo ""
echo "  停止: bash stop.sh"
echo "  日志: tail -f /tmp/stock_backend.log"
