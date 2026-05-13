#!/bin/bash
# A股量化投研系统 — 一键停止

echo "=== 停止系统 ==="

# 停止后端
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "✓ 后端已停止" || echo "- 后端未运行"

# 停止前端
pkill -f "next dev" 2>/dev/null && echo "✓ 前端已停止" || echo "- 前端未运行"

# 停止 Tunnel
pkill -f cloudflared 2>/dev/null && echo "✓ Tunnel 已停止" || echo "- Tunnel 未运行"

echo "=== 系统已停止 ==="
