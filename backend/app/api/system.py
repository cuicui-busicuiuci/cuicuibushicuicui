from datetime import datetime, date
from fastapi import APIRouter
from app.database import get_connection

router = APIRouter()


@router.get("/homepage")
def get_homepage_data():
    """首页数据聚合 — 单次请求替代9次调用"""
    from app.services.cache import cache

    cached_result = cache.get("homepage:data")
    if cached_result:
        return {"code": 0, "data": cached_result, "message": "ok (cached)"}

    from app.strategies.sentiment import sentiment_model
    from app.datasources.ths_hot_source import fetch_ths_hot
    from app.strategies.manager import strategy_manager
    from app.recommendation.daily import daily_recommender
    from app.api.strategy import _enrich_prices

    try:
        hot = fetch_ths_hot() or []
        if hot:
            hot = _enrich_prices(hot)
            # === 注入 market_cache 的 efinance 字段（板块/资金流/机构行为/连板） ===
            try:
                from app.services.market_cache import market_cache
                ef_data = market_cache.efinance_data
                if ef_data:
                    for s in hot:
                        code = s.get("code", "")
                        ef = ef_data.get(code, {})
                        if ef:
                            s.update(ef)
            except Exception as e:
                print(f"[首页] efinance 字段注入失败: {e}")
        sentiment = sentiment_model.analyze(hot) if hot else {"score": 50, "stage": "正常", "limit_up_count": 0, "max_board": 0, "action": "观望", "risk_level": "中"}

        strats = {}
        if hot:
            for s in strategy_manager.strategies:
                signals = strategy_manager.run_strategy(s.name, hot)
                strats[s.name] = [
                    {"code": sig.code, "name": sig.name, "price": sig.price,
                     "stop_loss": sig.stop_loss, "target_price": sig.target_price,
                     "reason": sig.reason, "confidence": sig.confidence}
                    for sig in signals[:5]
                ]

        total = sum(len(v) for v in strats.values())
        try:
            rec = daily_recommender.generate()
            recommendations = rec.get("recommendations", [])
        except Exception:
            recommendations = []

        result = {
            "sentiment": sentiment,
            "strategies": strats,
            "recommendations": recommendations,
            "total_signals": total,
            "timestamp": datetime.now().isoformat(),
        }

        cache.set("homepage:data", result, ttl=15)
        return {"code": 0, "data": result, "message": "ok"}
    except Exception as e:
        return {"code": 1, "data": None, "message": str(e)}


@router.get("/time")
def get_beijing_time():
    """北京时间 — 供调度器自检"""
    from datetime import timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=8)))
    return {
        "code": 0,
        "data": {
            "beijing_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.weekday(),
            "is_trading_day": 0 <= now.weekday() <= 4,
            "hour": now.hour,
            "minute": now.minute,
        },
        "message": "ok",
    }


@router.get("/cache")
def get_cache_status():
    """系统缓存状态"""
    from app.services.cache import cache
    return {"code": 0, "data": cache.get_stats(), "message": "ok"}


@router.post("/cache/clear")
def clear_cache(key: str = None):
    """清除缓存（不传key=全部清除）"""
    from app.services.cache import cache
    cache.delete(key) if key else cache.clear()
    return {"code": 0, "data": None, "message": "ok"}


@router.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "code": 0,
        "data": {
            "status": "ok",
            "db": db_status,
            "timestamp": datetime.now().isoformat(),
        },
        "message": "ok",
    }


@router.get("/sync-log")
def get_sync_log(limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return {
        "code": 0,
        "data": [dict(row) for row in rows],
        "message": "ok",
    }


@router.post("/sync/{task_name}")
def trigger_sync(task_name: str):
    from app.services.sync_service import run_sync_task

    result = run_sync_task(task_name)
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/scheduler")
def get_scheduler_info():
    """获取调度器状态"""
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    if not scheduler:
        return {"code": 0, "data": {"running": False, "jobs": []}, "message": "调度器未启动"}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "code": 0,
        "data": {
            "running": scheduler.running,
            "jobs": jobs,
        },
        "message": "ok",
    }


@router.post("/scheduler/trigger/{job_id}")
def trigger_job(job_id: str):
    """手动触发调度任务"""
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    if not scheduler:
        return {"code": 1, "data": None, "message": "调度器未启动"}

    job = scheduler.get_job(job_id)
    if not job:
        return {"code": 1, "data": None, "message": f"任务 {job_id} 不存在"}

    try:
        job.func()
        return {"code": 0, "data": {"job_id": job_id, "triggered": True}, "message": "ok"}
    except Exception as e:
        return {"code": 1, "data": None, "message": f"执行失败: {e}"}


# ---------- 多因子Alpha模型 ----------

@router.get("/alpha/report")
def get_alpha_report():
    """获取Alpha模型因子权重和表现"""
    from app.factors.alpha_model import alpha_model
    return {"code": 0, "data": alpha_model.get_report(), "message": "ok"}


@router.get("/alpha/score")
def get_alpha_score(code: str = ""):
    """获取单只或全部股票Alpha分"""
    from app.factors.alpha_model import alpha_model
    if code:
        from app.scanner.full_scanner import batch_tencent_quotes
        quotes = batch_tencent_quotes([code])
        if code in quotes:
            stock = quotes[code]
            stock["code"] = code
            score = alpha_model.compute_alpha(stock)
            return {"code": 0, "data": {"code": code, "alpha_score": score}, "message": "ok"}
        return {"code": 1, "data": None, "message": "未找到该股票"}
    return {"code": 0, "data": {"message": "请指定code参数"}, "message": "ok"}


# ---------- 因子IC ----------

@router.get("/factors/ic")
def get_factor_ic(horizon: int = 5):
    """获取因子IC统计"""
    from app.factors.ic_test import ic_tester
    results = ic_tester.compute_all_factors(horizon)
    eligible = ic_tester.get_eligible_factors(results)
    eliminated = ic_tester.get_elimination_candidates(results)
    return {
        "code": 0,
        "data": {
            "ic_results": results,
            "eligible_factors": eligible,
            "elimination_candidates": [{"factor": n, "reason": r} for n, r in eliminated],
            "horizon": horizon,
        },
        "message": "ok",
    }


# ---------- 策略健康 ----------

@router.get("/health/strategies")
def get_strategy_health():
    """获取策略健康评分和排名"""
    from app.health.scorer import health_scorer
    return {"code": 0, "data": health_scorer.get_report(), "message": "ok"}


@router.post("/health/recalculate")
def recalculate_strategy_health():
    """手动重新计算策略健康分"""
    from app.health.scorer import health_scorer
    from app.trading.trade_ledger import trade_ledger
    from app.strategies.manager import strategy_manager

    strategy_trades = {}
    for s in strategy_manager.strategies:
        trades = trade_ledger.query(strategy=s.name, status="closed", days=60, limit=200)
        strategy_trades[s.name] = [
            {"profit_pct": t.get("profit_pct", 0) or 0,
             "profit_amt": t.get("profit_amt", 0) or 0,
             "holding_days": t.get("holding_days", 0) or 0,
             "entry_time": t.get("entry_time", "")}
            for t in trades
        ]

    health_scorer.compute_all(strategy_trades)
    health_scorer._save_state()
    return {"code": 0, "data": health_scorer.get_report(), "message": "ok"}


# ---------- 复盘报告 ----------

@router.get("/review/today")
def get_today_review():
    """获取今日复盘报告"""
    from app.database import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM kv_store WHERE key = 'daily_review_report'"
    ).fetchone()
    if row:
        import json
        return {"code": 0, "data": json.loads(row["value"]), "message": "ok"}
    return {"code": 0, "data": None, "message": "今日报告尚未生成"}


@router.get("/recommendations/today")
def get_today_recommendations():
    """获取今日推荐池（从缓存）"""
    from app.database import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM kv_store WHERE key = 'daily_recommendations'"
    ).fetchone()
    if row:
        import json
        return {"code": 0, "data": json.loads(row["value"]), "message": "ok"}
    # 实时生成
    from app.recommendation.daily import daily_recommender
    return {"code": 0, "data": daily_recommender.generate(True), "message": "ok"}


@router.post("/optimization/run")
def trigger_post_market_optimization():
    """手动触发收盘优化流程"""
    from app.scheduler.daily_optimization import run_post_market_optimization
    result = run_post_market_optimization()
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/status")
def system_status():
    """系统综合状态"""
    import os, time, psutil
    from app.database import get_connection
    from app.trading.auto_trader import auto_trader

    # 数据库
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    # 磁盘（兼容 Windows 和 Linux）
    import sys
    disk_path = "C:\\" if sys.platform == "win32" else "/"
    disk = psutil.disk_usage(disk_path)
    disk_pct = disk.percent

    # 内存
    mem = psutil.virtual_memory()
    mem_pct = mem.percent

    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)

    # 容器
    uptime = time.time() - psutil.boot_time()
    uptime_h = round(uptime / 3600, 1)

    # 调度器
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    sched_running = scheduler.running if scheduler else False

    return {
        "code": 0,
        "data": {
            "api": "ok",
            "database": "ok" if db_ok else "error",
            "auto_trader": auto_trader.get_status(),
            "scheduler": sched_running,
            "system": {
                "hostname": os.uname().nodename if hasattr(os, "uname") else "docker",
                "uptime_hours": uptime_h,
                "cpu_pct": cpu_pct,
                "memory_pct": mem_pct,
                "disk_pct": disk_pct,
                "disk_free_gb": round(disk.free / 1024**3, 1),
            },
            "timestamp": datetime.now().isoformat(),
        },
        "message": "ok",
    }


@router.get("/tasks/status")
def tasks_status():
    """定时任务状态"""
    import app.main as main_module
    scheduler = getattr(main_module, "_scheduler", None)
    if not scheduler:
        return {"code": 0, "data": {"running": False, "jobs": []}, "message": "调度器未启动"}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending if hasattr(job, "pending") else False,
        })

    return {
        "code": 0,
        "data": {
            "running": scheduler.running,
            "total_jobs": len(jobs),
            "jobs": jobs,
        },
        "message": "ok",
    }


@router.get("/data/status")
def data_status():
    """数据状态"""
    from app.database import get_connection
    conn = get_connection()

    tables = ["trade_ledger", "trade_reports", "kv_store", "sync_log"]
    stats = {}
    for t in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
            stats[t] = row["cnt"] if row else 0
        except Exception:
            stats[t] = -1

    # 最新数据时间
    last_sync = conn.execute(
        "SELECT MAX(created_at) as t FROM sync_log").fetchone()

    return {
        "code": 0,
        "data": {
            "records": stats,
            "last_sync": last_sync["t"] if last_sync else None,
            "db_path": str(getattr(conn, "_database", "sqlite")),
        },
        "message": "ok",
    }


@router.get("/strategy/status")
def strategy_status():
    """策略状态汇总"""
    from app.health.scorer import health_scorer
    from app.factors.alpha_model import alpha_model
    from app.strategies.manager import strategy_manager

    strategies = strategy_manager.list_strategies()
    health = health_scorer.scores
    weights = health_scorer.get_weights()

    merged = []
    for s in strategies:
        name = s["name"]
        h = health.get(name, {})
        merged.append({
            "name": name,
            "description": s["description"],
            "status": h.get("status", "unknown"),
            "health_score": h.get("health_score", 0),
            "win_rate": h.get("win_rate", 0),
            "profit_loss_ratio": h.get("profit_loss_ratio", 0),
            "max_drawdown": h.get("max_drawdown", 0),
            "total_trades": h.get("total_trades", 0),
            "weight": weights.get(name, 0),
        })

    return {
        "code": 0,
        "data": {
            "strategies": sorted(merged, key=lambda x: x["health_score"], reverse=True),
            "alpha_factors": alpha_model.get_active_factors(),
            "factor_weights": alpha_model.weights,
        },
        "message": "ok",
    }


# ---------- 每日变动汇总（18点前查看当日所有变化） ----------

@router.get("/daily/report")
def get_daily_full_report(date_str: str = None):
    """每日完整变动报告 — 因子/策略/交易/回测/优化一目了然"""
    from app.database import get_connection
    from app.health.scorer import health_scorer
    from app.factors.alpha_model import alpha_model
    from app.trading.paper_engine import paper_engine
    from app.trading.auto_trader import auto_trader
    from app.trading.trade_ledger import trade_ledger
    from app.backtest.engine import backtest_engine

    if date_str is None:
        date_str = date.today().isoformat()

    conn = get_connection()

    # 1. 账户状态
    status = paper_engine.get_status()
    account = {
        "total_value": status["total_value"],
        "total_profit": status["total_profit"],
        "total_profit_pct": status["total_profit_pct"],
        "position_count": status["position_count"],
        "cash": status["cash"],
        "positions": status.get("positions", []),
    }

    # 2. 今日交易明细
    trades_today = trade_ledger.query(days=1, limit=100)
    buy_count = sum(1 for t in trades_today if t.get("direction") == "buy")
    sell_count = sum(1 for t in trades_today if t.get("direction") == "sell")
    pnl_today = sum(t.get("profit_amt", 0) or 0 for t in trades_today if t.get("status") == "closed")

    # 3. 因子变动
    factor_report = alpha_model.get_report()
    from app.factors.alpha_model import DEFAULT_WEIGHTS as _default_w
    default_w = _default_w
    factor_changes = []
    for name, w in factor_report["weights"].items():
        old = default_w.get(name, w)
        if abs(w - old) > 0.005:
            factor_changes.append({
                "factor": name,
                "old_weight": round(old, 3),
                "new_weight": round(w, 3),
                "change": round(w - old, 3),
                "active": name in factor_report["active_factors"],
            })

    # 4. 策略变动
    # 确保所有策略都有健康分（包括新增策略）
    try:
        from app.strategies.manager import strategy_manager
        for s in strategy_manager.strategies:
            if s.name not in health_scorer.scores:
                health_scorer.scores[s.name] = {
                    "health_score": HEALTH_DEFAULT_SCORE,
                    "win_rate": 0, "profit_loss_ratio": 0,
                    "max_drawdown": 0, "sharpe": 0,
                    "stability": 0, "trade_freq_score": 50,
                    "status": "active",
                    "consecutive_below_50": 0,
                    "total_trades": 0, "history": [],
                }
    except Exception:
        pass
    health = health_scorer.scores
    strategy_weights = health_scorer.get_weights()
    strategy_report = []
    for name, s in health.items():
        strategy_report.append({
            "name": name,
            "health_score": s["health_score"],
            "win_rate": s["win_rate"],
            "profit_loss_ratio": s["profit_loss_ratio"],
            "max_drawdown": s["max_drawdown"],
            "sharpe": s["sharpe"],
            "status": s["status"],
            "weight": strategy_weights.get(name, 0),
            "total_trades": s["total_trades"],
            "consecutive_below_50": s.get("consecutive_below_50", 0),
        })

    # 5. 回测结果（各策略真实数据回测）
    backtest_results = {}
    for name in health.keys():
        bt = backtest_engine.run_from_ledger(strategy=name)
        if bt.total_trades >= 3:
            backtest_results[name] = {
                "total_return": bt.total_return,
                "win_rate": bt.win_rate,
                "sharpe_ratio": bt.sharpe_ratio,
                "max_drawdown": bt.max_drawdown,
                "total_trades": bt.total_trades,
            }

    # 6. 优化记录（当日）
    optimizations = []
    try:
        from app.optimizer.auto_optimizer import auto_optimizer
        for opt in auto_optimizer.optimizations[-20:]:
            if opt.get("time", "")[:10] == date_str:
                optimizations.append(opt)
    except Exception:
        pass

    # 7. 引擎状态
    engine = auto_trader.get_status()

    # 汇总
    return {
        "code": 0,
        "data": {
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "account": account,
            "today_summary": {
                "total_trades": len(trades_today),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "today_pnl": round(pnl_today, 2),
            },
            "trades": trades_today[-20:],
            "factor_changes": factor_changes,
            "factor_weights": factor_report["weights"],
            "active_factors": factor_report["active_factors"],
            "strategy_health": sorted(strategy_report, key=lambda x: x["health_score"], reverse=True),
            "backtest_results": backtest_results,
            "optimizations_today": optimizations,
            "engine_status": engine,
        },
        "message": "ok",
    }


