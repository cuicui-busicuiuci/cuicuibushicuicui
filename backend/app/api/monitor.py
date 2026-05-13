from fastapi import APIRouter

router = APIRouter()


@router.get("/report")
def get_monitor_report():
    from app.scheduler.monitor import market_monitor
    report = market_monitor.generate_report()
    return {"code": 0, "data": report, "message": "ok"}


@router.get("/alerts")
def get_alerts():
    from app.scheduler.monitor import market_monitor
    alerts = market_monitor.get_alerts()
    return {"code": 0, "data": alerts, "message": "ok"}


@router.post("/start")
def start_monitoring():
    from app.scheduler.monitor import market_monitor
    market_monitor.start_monitoring()
    return {"code": 0, "data": {"message": "监控已启动"}, "message": "ok"}


@router.post("/stop")
def stop_monitoring():
    from app.scheduler.monitor import market_monitor
    market_monitor.stop_monitoring()
    return {"code": 0, "data": {"message": "监控已停止"}, "message": "ok"}
