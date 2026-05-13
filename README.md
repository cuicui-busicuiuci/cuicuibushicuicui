# A股量化投研系统

A股选股软件 - 行情/新闻/因子/策略/回测

## 技术栈

- **后端**: Python 3.13 + FastAPI + SQLite + APScheduler
- **数据源**: mootdx / 腾讯财经 / 东财 / akshare / 同花顺

## 快速开始

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
uvicorn app.main:app --reload --port 8000

# 4. 访问 API 文档
# http://localhost:8000/docs
```

## API 接口

| 模块 | 接口 | 说明 |
|------|------|------|
| 系统 | GET /api/system/health | 健康检查 |
| 行情 | GET /api/market/quote/{code} | 单股实时行情 |
| 行情 | GET /api/market/kline/{code} | K线数据 |
| 估值 | GET /api/valuation/{code} | 完整估值分析 |
| 研报 | GET /api/report/{code} | 研报列表 |
| 信号 | GET /api/signal/hot | 当日热点 |
| 信号 | GET /api/signal/north | 北向资金 |
| 新闻 | GET /api/news/{code} | 个股新闻 |

## 数据源

| 数据源 | 用途 | 特点 |
|--------|------|------|
| mootdx | K线/盘口/财务 | TCP直连，不封IP |
| 腾讯财经 | PE/PB/市值 | HTTP，低风险 |
| 东财 | 研报/PDF | Python封装 |
| akshare | 新闻/公告/一致预期 | 综合数据源 |
| 同花顺 | 热点/北向 | 零鉴权 |

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI入口
│   ├── config.py            # 配置
│   ├── database.py          # SQLite连接
│   ├── models/              # 数据模型
│   ├── db/                  # DAO层
│   ├── datasources/         # 数据适配层
│   ├── services/            # 业务逻辑层
│   ├── api/                 # API路由
│   └── scheduler/           # 定时任务
├── data/                    # SQLite数据库
└── requirements.txt
```
