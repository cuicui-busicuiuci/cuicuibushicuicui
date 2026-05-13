#!/bin/bash
# =============================================
# A股量化投研系统 — 云服务器一键部署
# 适用: Ubuntu 22.04+ / Debian 12+ (2核2G+)
# 用法: wget -O - <url>/server-deploy.sh | bash
#       或: bash server-deploy.sh
# =============================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

PROJECT_DIR="/opt/stock-ai-platform"
NGINX_CONF="/etc/nginx/sites-available/stock-ai"
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "YOUR_SERVER_IP")

echo "============================================"
echo "  A股量化投研系统 - 云服务器部署"
echo "============================================"
echo ""

# ---- 1. 系统依赖 ----
log "更新系统包..."
apt-get update -qq && apt-get upgrade -y -qq

log "安装基础依赖..."
apt-get install -y -qq curl wget git nginx certbot python3-certbot-nginx \
    build-essential python3-pip python3-venv nodejs npm 2>/dev/null || true

# Node.js 22 (Next.js 需要)
if ! node -v | grep -q "v22"; then
    log "安装 Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -qq nodejs
fi

# ---- 2. 部署后端 ----
log "部署后端..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 如果通过git部署，取消下面注释:
# git clone https://github.com/your/repo.git . || true

# 手动拷贝方式：用scp上传项目到 /opt/stock-ai-platform/
# scp -r backend/ frontend/ user@server:/opt/stock-ai-platform/

cd "$PROJECT_DIR/backend"

python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
deactivate

# 创建 systemd 服务
cat > /etc/systemd/system/stock-backend.service << 'SVC'
[Unit]
Description=Stock AI Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stock-ai-platform/backend
ExecStart=/opt/stock-ai-platform/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8017
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Shanghai

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable stock-backend
systemctl restart stock-backend
log "后端服务已启动 (端口 8017)"

# ---- 3. 部署前端 ----
log "构建前端 (production模式)..."
cd "$PROJECT_DIR/frontend"
npm install --silent
NEXT_PUBLIC_API_URL='' npm run build

# systemd 前端
cat > /etc/systemd/system/stock-frontend.service << 'SVC'
[Unit]
Description=Stock AI Frontend
After=network.target stock-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stock-ai-platform/frontend
Environment=NODE_ENV=production
Environment=NEXT_PUBLIC_API_URL=
Environment=PORT=3000
Environment=TZ=Asia/Shanghai
ExecStart=/usr/bin/node /opt/stock-ai-platform/frontend/.next/standalone/server.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable stock-frontend
systemctl restart stock-frontend
log "前端服务已启动 (端口 3000)"

# ---- 4. Nginx 反向代理 ----
log "配置 Nginx 反向代理..."
cat > "$NGINX_CONF" << 'NGX'
server {
    listen 80;
    server_name _;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8017;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8017;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # SSE
    location /api/trade/stream {
        proxy_pass http://127.0.0.1:8017;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        chunked_transfer_encoding on;
    }

    client_max_body_size 50m;
}
NGX

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "Nginx 已配置 (端口 80)"

# ---- 5. 防火墙 ----
log "配置防火墙..."
ufw allow 80/tcp 2>/dev/null || warn "ufw 未安装，请手动开放 80 端口"
ufw allow 443/tcp 2>/dev/null || true

# ---- 6. 验证 ----
sleep 3
echo ""
echo "============================================"
echo "  部署完成!"
echo "============================================"
echo ""

if curl -s http://127.0.0.1:8017/api/system/health > /dev/null 2>&1; then
    log "后端 API: 正常"
else
    warn "后端 API: 请检查 journalctl -u stock-backend -f"
fi

if curl -s http://127.0.0.1:3000 > /dev/null 2>&1; then
    log "前端页面: 正常"
else
    warn "前端页面: 请检查 journalctl -u stock-frontend -f"
fi

echo ""
echo "访问地址: http://${SERVER_IP}"
echo ""
echo "管理命令:"
echo "  systemctl status stock-backend   # 后端状态"
echo "  systemctl status stock-frontend  # 前端状态"
echo "  journalctl -u stock-backend -f   # 后端日志"
echo "  journalctl -u stock-frontend -f  # 前端日志"
echo ""
echo "配置HTTPS (推荐):"
echo "  certbot --nginx -d your-domain.com"
echo ""
echo "安全组/防火墙: 放行 80, 443 端口"
