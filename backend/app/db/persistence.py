"""扫描结果和推荐数据持久化"""
import json
from datetime import datetime, date
from app.database import get_connection


def save_scan_session(results: dict) -> int:
    """保存一次全A扫描会话，返回session_id"""
    conn = get_connection()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO scan_sessions (started_at, ended_at, total_scanned, results_count, scan_time_sec, status)
           VALUES (?, ?, ?, ?, ?, 'completed')""",
        (now, now, results.get("total_scanned", 0),
         results.get("results_count", 0), results.get("scan_time_seconds", 0))
    )
    session_id = cursor.lastrowid

    items = results.get("results", [])
    for r in items:
        conn.execute(
            """INSERT INTO scan_items
               (session_id, code, name, price, change_pct, mcap, turnover_pct,
                pe_ttm, pb, signal_count, avg_confidence, composite_score,
                tech_score, strategies, tech_signals, top_reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id,
             r.get("code"), r.get("name"), r.get("price"), r.get("change_pct"),
             r.get("mcap"), r.get("turnover_pct"), r.get("pe_ttm"), r.get("pb"),
             r.get("signal_count", 0), r.get("avg_confidence", 0),
             r.get("composite_score", 0), r.get("tech_score", 0),
             json.dumps(r.get("strategies", []), ensure_ascii=False),
             json.dumps(r.get("tech_signals", []), ensure_ascii=False),
             (r.get("signals", [{}]) or [{}])[0].get("reason", "")[:80] if r.get("signals") else "",
             now)
        )
    return session_id


def save_daily_recommendations(data: dict):
    """保存每日推荐结果"""
    conn = get_connection()
    today = date.today().isoformat()
    now = datetime.now().isoformat()

    recs = data.get("recommendations", [])
    if not recs:
        return 0

    for r in recs:
        conn.execute(
            """INSERT OR REPLACE INTO daily_picks
               (date, code, name, level, price, stop_loss, target, confidence, reason, risk, strategy, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, r.get("code"), r.get("name"), r.get("level", ""),
             r.get("price", 0), r.get("stop_loss", 0), r.get("target_price", 0),
             r.get("confidence", 0), r.get("reason", "")[:200], r.get("risk", "")[:100],
             r.get("strategy", ""), now)
        )
    return len(recs)


def save_strategy_signals(strategies: dict):
    """保存各策略信号"""
    conn = get_connection()
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    count = 0

    for strategy_name, signals in strategies.items():
        for s in signals:
            conn.execute(
                """INSERT INTO signal_log
                   (date, code, name, strategy, confidence, price, stop_loss, target, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (today, s.get("code"), s.get("name"), strategy_name,
                 s.get("confidence", 0), s.get("price", 0),
                 s.get("stop_loss", 0), s.get("target_price", 0),
                 s.get("reason", "")[:200], now)
            )
            count += 1
    return count


def get_scan_history(limit: int = 10) -> list:
    """获取历史扫描会话"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scan_sessions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_scan_items(session_id: int, min_score: float = 0, limit: int = 50) -> list:
    """获取某次扫描的个股结果"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM scan_items
           WHERE session_id = ? AND composite_score >= ?
           ORDER BY composite_score DESC LIMIT ?""",
        (session_id, min_score, limit)
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["strategies"] = json.loads(d.get("strategies", "[]"))
        d["tech_signals"] = json.loads(d.get("tech_signals", "[]"))
        results.append(d)
    return results


def get_daily_picks(date_str: str = None) -> list:
    """获取某日推荐"""
    conn = get_connection()
    if date_str is None:
        date_str = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM daily_picks WHERE date = ? ORDER BY confidence DESC",
        (date_str,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_signal_stats(days: int = 7) -> list:
    """获取最近N天的策略信号统计"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT date, strategy, COUNT(*) as cnt, AVG(confidence) as avg_conf
           FROM signal_log
           WHERE date >= date('now', ?)
           GROUP BY date, strategy
           ORDER BY date DESC, cnt DESC""",
        (f"-{days} days",)
    ).fetchall()
    return [dict(r) for r in rows]


def get_stock_history(code: str, limit: int = 20) -> list:
    """查询某只股票的历史扫描记录"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.*, ss.started_at as scan_time
           FROM scan_items si
           JOIN scan_sessions ss ON si.session_id = ss.id
           WHERE si.code = ?
           ORDER BY ss.id DESC LIMIT ?""",
        (code, limit)
    ).fetchall()
    return [dict(r) for r in rows]
