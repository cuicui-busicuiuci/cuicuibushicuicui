import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.scanner.full_scanner import full_market_scan, get_all_stocks

router = APIRouter()


@router.get("/full")
def run_full_scan(
    max_stocks: int = Query(0, description="扫描数量上限, 0=全部"),
    min_score: int = Query(40, description="最低综合分数"),
):
    """全市场扫描"""
    result = full_market_scan(max_stocks=max_stocks, min_score=min_score)
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/top")
def get_top_picks(limit: int = Query(20, description="返回前N只")):
    """快速获取Top选股"""
    result = full_market_scan(max_stocks=0, min_score=50)
    results = result.get("results", [])[:limit]
    result["results"] = results
    result["results_count"] = len(results)
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/universe")
def get_universe_info():
    """获取A股全量信息"""
    stocks = get_all_stocks()
    return {
        "code": 0,
        "data": {
            "total": len(stocks),
            "markets": {
                "SH": len([s for s in stocks if s["code"].startswith("6")]),
                "SZ": len([s for s in stocks if s["code"].startswith(("0", "3"))]),
            },
        },
        "message": "ok",
    }


@router.websocket("/live")
async def live_scan_ws(ws: WebSocket):
    """实时扫描WebSocket - 边扫描边推送结果"""
    from app.api.ws_manager import ws_manager
    from app.scanner.full_scanner import pre_filter, scan_stock
    from app.strategies.manager import strategy_manager
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    await ws_manager.connect(ws)

    try:
        await ws_manager.send_to(ws, {"type": "scan_start", "message": "开始全市场扫描..."})

        stocks = get_all_stocks()
        candidates = pre_filter(stocks)

        await ws_manager.send_to(ws, {
            "type": "scan_progress",
            "total": len(candidates),
            "message": f"预筛选完成: {len(candidates)}/{len(stocks)} 只",
        })

        results = []
        batch_size = 200
        workers = min(20, len(candidates) // 10 + 1)
        completed = 0

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            batch_results = []

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(scan_stock, s, strategy_manager, None): s for s in batch}
                for future in as_completed(futures):
                    completed += 1
                    try:
                        r = future.result(timeout=10)
                        if r and r["composite_score"] >= 40:
                            batch_results.append(r)
                    except Exception:
                        pass

            batch_results.sort(key=lambda x: x["composite_score"], reverse=True)
            results.extend(batch_results)

            # 每批推送进度和Top结果
            try:
                await ws_manager.send_to(ws, {
                    "type": "scan_progress",
                    "completed": completed,
                    "total": len(candidates),
                    "found": len(results),
                    "pct": round(completed / len(candidates) * 100, 1),
                    "batch_top": batch_results[:5],
                })
            except Exception:
                break

        results.sort(key=lambda x: x["composite_score"], reverse=True)

        await ws_manager.send_to(ws, {
            "type": "scan_complete",
            "total_scanned": len(candidates),
            "results_count": len(results),
            "scan_time_seconds": 0,
            "results": results[:100],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws_manager.send_to(ws, {"type": "scan_error", "message": str(e)})
        except Exception:
            pass
    finally:
        await ws_manager.disconnect(ws)
