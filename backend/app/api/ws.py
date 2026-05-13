import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.ws_manager import ws_manager, gather_market_data

router = APIRouter()


@router.websocket("/market")
async def market_websocket(ws: WebSocket):
    """实时市场数据推送"""
    await ws_manager.connect(ws)
    try:
        # 首次连接立即推送全量数据
        data = gather_market_data()
        await ws_manager.send_to(ws, data)

        # 持续接收客户端心跳并保持连接
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                if msg == "ping":
                    await ws_manager.send_to(ws, {"type": "pong"})
                elif msg == "refresh":
                    data = gather_market_data()
                    await ws_manager.send_to(ws, data)
            except asyncio.TimeoutError:
                # 心跳超时发送ping检查
                try:
                    await ws_manager.send_to(ws, {"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] 异常: {e}")
    finally:
        await ws_manager.disconnect(ws)


@router.websocket("/quotes")
async def quotes_websocket(ws: WebSocket):
    """实时行情推送（单只股票）"""
    await ws_manager.connect(ws)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("action") == "subscribe" and data.get("code"):
                    code = data["code"]
                    from app.datasources.tencent_source import fetch_tencent_quote
                    quote = fetch_tencent_quote(code)
                    await ws_manager.send_to(ws, {
                        "type": "quote",
                        "code": code,
                        "data": quote,
                    })
            except asyncio.TimeoutError:
                try:
                    await ws_manager.send_to(ws, {"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
