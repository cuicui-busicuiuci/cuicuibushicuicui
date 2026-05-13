import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.database import init_db
from app.api.system import router as system_router
from app.api.market import router as market_router
from app.api.valuation import router as valuation_router
from app.api.report import router as report_router
from app.api.signal import router as signal_router
from app.api.news import router as news_router
from app.api.strategy import router as strategy_router
from app.api.backtest import router as backtest_router
from app.api.recommendation import router as recommendation_router
from app.api.risk import router as risk_router
from app.api.factor import router as factor_router
from app.api.news_analysis import router as news_analysis_router
from app.api.optimizer import router as optimizer_router
from app.api.learning import router as learning_router
from app.api.monitor import router as monitor_router
from app.api.models import router as models_router
from app.api.ws import router as ws_router
from app.api.scan import router as scan_router
from app.api.history import router as history_router
from app.api.trade import router as trade_router


_scheduler = None
_broadcast_running = False


async def broadcast_market_data_loop():
    """后台异步循环：每30秒向所有WebSocket客户端广播最新市场数据"""
    global _broadcast_running
    from app.api.ws_manager import ws_manager, gather_market_data

    _broadcast_running = True
    print("[广播] 实时数据广播已启动 (每30秒)")

    while _broadcast_running:
        try:
            if ws_manager.active_count > 0:
                data = gather_market_data()
                await ws_manager.broadcast(data)
        except Exception as e:
            print(f"[广播] 异常: {e}")
        await asyncio.sleep(30)


def start_async_broadcast(loop):
    """在事件循环中启动广播任务"""
    asyncio.set_event_loop(loop)
    loop.create_task(broadcast_market_data_loop())
    loop.run_forever()


def start_scheduler():
    """在后台线程启动定时任务调度器"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from app.scheduler.jobs import (
            sync_realtime_quotes, sync_daily_kline, sync_ths_hot,
            sync_north_flow, sync_reports, sync_stock_list,
            morning_monitor, afternoon_monitor, stop_monitoring,
            generate_morning_report, generate_afternoon_report,
            auto_full_scan, save_daily_signals,
            generate_daily_trade_report,
        )

        scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

        # 数据同步任务
        scheduler.add_job(sync_realtime_quotes, CronTrigger(day_of_week="1-5", hour="9,10,11,13,14", minute="31"),
                          id="sync_quotes", replace_existing=True)
        scheduler.add_job(sync_daily_kline, CronTrigger(day_of_week="1-5", hour="16", minute="0"),
                          id="sync_kline", replace_existing=True)
        scheduler.add_job(sync_ths_hot, CronTrigger(day_of_week="1-5", hour="9,10,11,13,14", minute="35"),
                          id="sync_ths_hot", replace_existing=True)
        scheduler.add_job(sync_north_flow, CronTrigger(day_of_week="1-5", hour="9,10,11,13,14", minute="40"),
                          id="sync_north", replace_existing=True)
        scheduler.add_job(sync_stock_list, CronTrigger(day_of_week="1-5", hour="8", minute="0"),
                          id="sync_stocks", replace_existing=True)

        # 监控任务
        scheduler.add_job(morning_monitor, CronTrigger(day_of_week="1-5", hour="9", minute="30"),
                          id="morning_monitor", replace_existing=True)
        scheduler.add_job(generate_morning_report, CronTrigger(day_of_week="1-5", hour="11", minute="45"),
                          id="morning_report", replace_existing=True)
        scheduler.add_job(afternoon_monitor, CronTrigger(day_of_week="1-5", hour="13", minute="0"),
                          id="afternoon_monitor", replace_existing=True)
        scheduler.add_job(generate_afternoon_report, CronTrigger(day_of_week="1-5", hour="15", minute="30"),
                          id="afternoon_report", replace_existing=True)
        scheduler.add_job(stop_monitoring, CronTrigger(day_of_week="1-5", hour="15", minute="10"),
                          id="stop_monitor", replace_existing=True)

        # 全A自动扫描（盘中每30分钟）
        scheduler.add_job(auto_full_scan, CronTrigger(day_of_week="1-5", hour="9,10,11,13,14", minute="5,35"),
                          id="auto_scan", replace_existing=True)

        # 信号入库（盘中每15分钟）
        scheduler.add_job(save_daily_signals, CronTrigger(day_of_week="1-5", hour="9-14", minute="*/15"),
                          id="save_signals", replace_existing=True)

        # 模拟交易（已由 auto_trader 引擎接管，秒级响应）
        # run_daily_trading 保留为手动触发备用

        # 每日交易报告（收盘后15:10）
        scheduler.add_job(generate_daily_trade_report, CronTrigger(day_of_week="1-5", hour="15", minute="10"),
                          id="trade_report", replace_existing=True)

        scheduler.start()
        print("[调度器] 定时任务已启动")

        import app.main as main_module
        main_module._scheduler = scheduler

    except Exception as e:
        print(f"[调度器] 启动失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # 启动APScheduler（后台线程）
    t = threading.Thread(target=start_scheduler, daemon=True)
    t.start()

    # 启动WebSocket广播循环（独立事件循环线程）
    broadcast_loop = asyncio.new_event_loop()
    bt = threading.Thread(target=start_async_broadcast, args=(broadcast_loop,), daemon=True)
    bt.start()

    # 启动自动交易引擎
    try:
        from app.trading.auto_trader import auto_trader
        from app.api.trade import _on_trade_callback, _on_cycle_callback
        auto_trader.on_trade(_on_trade_callback)
        auto_trader.on_cycle(_on_cycle_callback)
        auto_trader.start()
        print("[启动] 自动交易引擎已启动")
    except Exception as e:
        print(f"[启动] 自动交易引擎启动失败: {e}")

    # 启动自动策略优化器
    try:
        from app.optimizer.auto_optimizer import auto_optimizer
        auto_optimizer.start()
        print("[启动] 自动策略优化器已启动")
    except Exception as e:
        print(f"[启动] 自动优化器启动失败: {e}")

    yield

    # 停止自动交易引擎
    try:
        from app.trading.auto_trader import auto_trader
        auto_trader.stop()
    except Exception:
        pass

    # 停止自动优化器
    try:
        from app.optimizer.auto_optimizer import auto_optimizer
        auto_optimizer.stop()
    except Exception:
        pass

    # 停止广播
    global _broadcast_running
    _broadcast_running = False
    broadcast_loop.call_soon_threadsafe(broadcast_loop.stop)


app = FastAPI(
    title="A股量化投研系统",
    description="A股选股软件 - 行情/新闻/因子/策略/回测",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix="/api/system", tags=["系统"])
app.include_router(market_router, prefix="/api/market", tags=["行情"])
app.include_router(valuation_router, prefix="/api/valuation", tags=["估值"])
app.include_router(report_router, prefix="/api/report", tags=["研报"])
app.include_router(signal_router, prefix="/api/signal", tags=["信号"])
app.include_router(news_router, prefix="/api/news", tags=["新闻"])
app.include_router(strategy_router, prefix="/api/strategy", tags=["策略"])
app.include_router(backtest_router, prefix="/api/backtest", tags=["回测"])
app.include_router(recommendation_router, prefix="/api/recommendation", tags=["推荐"])
app.include_router(risk_router, prefix="/api/risk", tags=["风控"])
app.include_router(factor_router, prefix="/api/factor", tags=["因子"])
app.include_router(news_analysis_router, prefix="/api/news-analysis", tags=["新闻分析"])
app.include_router(optimizer_router, prefix="/api/optimizer", tags=["优化器"])
app.include_router(learning_router, prefix="/api/learning", tags=["自学习"])
app.include_router(monitor_router, prefix="/api/monitor", tags=["监控"])
app.include_router(models_router, prefix="/api/models", tags=["模型"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
app.include_router(scan_router, prefix="/api/scan", tags=["全市场扫描"])
app.include_router(history_router, prefix="/api/history", tags=["历史数据"])
app.include_router(trade_router, prefix="/api/trade", tags=["模拟交易"])


@app.get("/")
def root():
    return {"message": "A股量化投研系统 API", "version": "0.3.0", "docs": "/docs"}
