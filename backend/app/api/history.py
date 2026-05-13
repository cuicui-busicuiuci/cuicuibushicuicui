"""历史数据查询API"""
from fastapi import APIRouter, Query
from datetime import date

router = APIRouter()


@router.get("/scans")
def list_scans(limit: int = Query(10, description="返回条数")):
    """获取历史扫描会话列表"""
    from app.db.persistence import get_scan_history
    data = get_scan_history(limit)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/scans/{session_id}")
def get_scan_detail(
    session_id: int,
    min_score: float = Query(0, description="最低分数"),
    limit: int = Query(50, description="返回条数"),
):
    """获取某次扫描的详细结果"""
    from app.db.persistence import get_scan_items
    data = get_scan_items(session_id, min_score, limit)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/picks")
def get_picks_history(
    date_str: str = Query(None, description="日期 YYYY-MM-DD，默认今天"),
):
    """获取每日推荐历史"""
    from app.db.persistence import get_daily_picks
    data = get_daily_picks(date_str)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/signals")
def get_signal_stats(days: int = Query(7, description="统计天数")):
    """获取策略信号统计"""
    from app.db.persistence import get_signal_stats
    data = get_signal_stats(days)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/stock/{code}")
def get_stock_history(
    code: str,
    limit: int = Query(20, description="返回条数"),
):
    """查询某只股票的历史扫描记录"""
    from app.db.persistence import get_stock_history
    data = get_stock_history(code, limit)
    return {"code": 0, "data": data, "message": "ok"}


@router.get("/dashboard")
def get_dashboard():
    """获取仪表盘概览数据"""
    from app.database import get_connection
    conn = get_connection()

    today = date.today().isoformat()

    # 今日推荐数
    today_picks = conn.execute(
        "SELECT COUNT(*) as cnt FROM daily_picks WHERE date = ?", (today,)
    ).fetchone()["cnt"]

    # 今日信号数
    today_signals = conn.execute(
        "SELECT COUNT(*) as cnt FROM signal_log WHERE date = ?", (today,)
    ).fetchone()["cnt"]

    # 最新扫描
    latest_scan = conn.execute(
        "SELECT * FROM scan_sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # 近7天信号趋势
    signal_trend = conn.execute(
        """SELECT date, COUNT(*) as cnt, AVG(confidence) as avg_conf
           FROM signal_log
           WHERE date >= date('now', '-7 days')
           GROUP BY date ORDER BY date"""
    ).fetchall()

    # 近7天策略分布
    strategy_dist = conn.execute(
        """SELECT strategy, COUNT(*) as cnt
           FROM signal_log
           WHERE date >= date('now', '-7 days')
           GROUP BY strategy ORDER BY cnt DESC"""
    ).fetchall()

    return {
        "code": 0,
        "data": {
            "today": {
                "picks": today_picks,
                "signals": today_signals,
            },
            "latest_scan": dict(latest_scan) if latest_scan else None,
            "signal_trend": [dict(r) for r in signal_trend],
            "strategy_distribution": [dict(r) for r in strategy_dist],
        },
        "message": "ok",
    }
