from datetime import datetime
from app.database import get_connection


def run_sync_task(task_name: str) -> dict:
    conn = get_connection()
    started_at = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO sync_log (task_name, status, started_at) VALUES (?, 'running', ?)",
        (task_name, started_at),
    )

    try:
        if task_name == "ths_hot":
            from app.datasources.ths_hot_source import fetch_ths_hot
            data = fetch_ths_hot()
            detail = f"获取 {len(data)} 条热点数据"
        elif task_name == "north_flow":
            from app.datasources.ths_north_source import fetch_north_realtime
            data = fetch_north_realtime()
            detail = f"获取北向资金数据"
        elif task_name == "reports":
            detail = "研报同步任务已触发"
        elif task_name == "stock_list":
            detail = "股票列表同步任务已触发"
        else:
            detail = f"未知任务: {task_name}"

        ended_at = datetime.now().isoformat()
        conn.execute(
            "UPDATE sync_log SET status='success', detail=?, ended_at=? WHERE task_name=? AND status='running'",
            (detail, ended_at, task_name),
        )
        return {"task": task_name, "status": "success", "detail": detail}

    except Exception as e:
        ended_at = datetime.now().isoformat()
        conn.execute(
            "UPDATE sync_log SET status='failed', detail=?, ended_at=? WHERE task_name=? AND status='running'",
            (str(e), ended_at, task_name),
        )
        return {"task": task_name, "status": "failed", "error": str(e)}
