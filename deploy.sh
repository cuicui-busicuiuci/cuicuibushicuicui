#!/bin/bash
# A股量化投研系统 — 一键部署脚本
# 用法: bash deploy.sh

set -e

echo "=== A股量化投研系统 部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[错误] 请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[错误] 请先安装 Docker Compose"
    exit 1
fi

COMPOSE="docker-compose"
if docker compose version &> /dev/null 2>&1; then
    COMPOSE="docker compose"
fi

echo "[1/3] 构建镜像..."
$COMPOSE build

echo "[2/3] 启动服务..."
$COMPOSE up -d

echo "[3/3] 等待服务就绪..."
sleep 5

# 健康检查
if curl -s http://localhost:8017/api/system/health > /dev/null 2>&1; then
    echo "✓ 后端 API 正常: http://localhost:8017"
else
    echo "✗ 后端启动失败，请检查日志: $COMPOSE logs backend"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✓ 前端页面正常: http://localhost:3000"
else
    echo "✗ 前端启动失败，请检查日志: $COMPOSE logs frontend"
fi

echo ""
echo "=== 部署完成 ==="
echo "内网访问: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):3000"
echo ""
echo "配置外网访问:"
echo "  1. 云服务器安全组放行 8017 和 3000 端口"
echo "  2. 或者用 Cloudflare Tunnel:"
echo "     cloudflared tunnel --url http://localhost:3000"
echo ""
echo "查看日志: $COMPOSE logs -f"
echo "停止服务: $COMPOSE down"
