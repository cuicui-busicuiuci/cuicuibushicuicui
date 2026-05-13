"""
VeighNa(vnpy) 模拟交易引擎
集成到A股量化投研系统：初始10万资金、自动执行策略信号、每日盈亏报告
"""
import json
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict


@dataclass
class Order:
    order_id: str
    code: str
    name: str
    direction: str  # buy/sell
    price: float
    volume: int    # 股数
    status: str    # pending/filled/cancelled
    strategy: str
    reason: str
    created_at: str
    filled_at: str = ""
    filled_price: float = 0


@dataclass
class Position:
    code: str
    name: str
    volume: int
    avg_cost: float
    current_price: float = 0
    market_value: float = 0
    profit_pct: float = 0
    profit_amt: float = 0
    holding_days: int = 0
    buy_date: str = ""
    strategy: str = ""


class PaperTradingEngine:
    """vnpy风格的模拟交易引擎"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.order_counter = 0
        self.today_trades: List[Order] = []
        self.start_date = date.today().isoformat()

        # 风控参数
        self.max_positions = 5          # 最大持仓数
        self.max_position_pct = 0.20    # 单票最大仓位20%
        self.stop_loss_pct = 0.05       # 止损5%
        self.take_profit_pct = 0.15     # 止盈15%
        self.min_buy_volume = 100       # 最小买入100股(A股1手)

    def _new_order_id(self) -> str:
        self.order_counter += 1
        return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{self.order_counter:04d}"

    @property
    def total_value(self) -> float:
        pos_value = sum(p.market_value for p in self.positions.values())
        return self.cash + pos_value

    @property
    def total_profit(self) -> float:
        return self.total_value - self.initial_capital

    @property
    def total_profit_pct(self) -> float:
        if self.initial_capital > 0:
            return round(self.total_profit / self.initial_capital * 100, 2)
        return 0

    def process_signals(self, signals: List[dict], quotes: Dict[str, dict]):
        """处理策略信号，生成交易订单"""
        today_orders = []

        # 1. 先检查止损止盈
        self._check_stop_loss_take_profit(quotes, today_orders)

        # 2. 处理买入信号
        buy_signals = [s for s in signals if s.get("signal_type") == "buy"]
        buy_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)

        for sig in buy_signals:
            if len(self.positions) >= self.max_positions:
                break

            code = sig.get("code", "")
            if not code or code in self.positions:
                continue

            # 获取实时价格
            q = quotes.get(code, {})
            price = q.get("price", sig.get("price", 0))
            if not price or price <= 0:
                continue

            # 计算买入数量（不超过单票仓位上限）
            max_value = self.total_value * self.max_position_pct
            max_vol = int(max_value / price / 100) * 100
            if max_vol < self.min_buy_volume:
                continue

            buy_vol = min(max_vol, int(self.cash * 0.2 / price / 100) * 100)
            if buy_vol < self.min_buy_volume:
                continue

            cost = buy_vol * price
            if cost > self.cash:
                buy_vol = int(self.cash / price / 100) * 100
                cost = buy_vol * price

            if buy_vol < self.min_buy_volume:
                continue

            # 创建订单
            order = Order(
                order_id=self._new_order_id(),
                code=code,
                name=q.get("name", sig.get("name", "")),
                direction="buy",
                price=price,
                volume=buy_vol,
                status="filled",
                strategy=sig.get("strategy", ""),
                reason=sig.get("reason", "")[:80],
                created_at=datetime.now().isoformat(),
                filled_at=datetime.now().isoformat(),
                filled_price=price,
            )

            # 更新账户
            self.cash -= cost
            self.positions[code] = Position(
                code=code,
                name=order.name,
                volume=buy_vol,
                avg_cost=price,
                current_price=price,
                market_value=cost,
                buy_date=date.today().isoformat(),
                strategy=order.strategy,
            )
            self.orders.append(order)
            today_orders.append(order)

        self.today_trades.extend(today_orders)
        if today_orders:
            self.save_state()
        return today_orders

    def _check_stop_loss_take_profit(self, quotes: dict, orders_out: list):
        """检查止损止盈条件"""
        for code, pos in list(self.positions.items()):
            q = quotes.get(code, {})
            current_price = q.get("price", pos.current_price)
            if not current_price or current_price <= 0:
                continue

            pos.current_price = current_price
            pos.market_value = current_price * pos.volume
            pos.profit_pct = round((current_price - pos.avg_cost) / pos.avg_cost * 100, 2)
            pos.profit_amt = round((current_price - pos.avg_cost) * pos.volume, 2)

            sell_reason = ""
            if pos.profit_pct <= -self.stop_loss_pct * 100:
                sell_reason = f"止损: {pos.profit_pct:.1f}%"
            elif pos.profit_pct >= self.take_profit_pct * 100:
                sell_reason = f"止盈: {pos.profit_pct:.1f}%"

            if sell_reason:
                order = Order(
                    order_id=self._new_order_id(),
                    code=code, name=pos.name,
                    direction="sell", price=current_price,
                    volume=pos.volume, status="filled",
                    strategy=pos.strategy, reason=sell_reason,
                    created_at=datetime.now().isoformat(),
                    filled_at=datetime.now().isoformat(),
                    filled_price=current_price,
                )
                self.cash += pos.market_value
                self.orders.append(order)
                orders_out.append(order)
                del self.positions[code]
                self.save_state()

    def update_positions(self, quotes: Dict[str, dict]):
        """更新持仓市值"""
        for code, pos in self.positions.items():
            q = quotes.get(code, {})
            if q.get("price", 0) > 0:
                pos.current_price = q["price"]
                pos.market_value = pos.current_price * pos.volume
                pos.profit_pct = round((pos.current_price - pos.avg_cost) / pos.avg_cost * 100, 2)
                pos.profit_amt = round((pos.current_price - pos.avg_cost) * pos.volume, 2)
                pos.holding_days = (date.today() - date.fromisoformat(pos.buy_date)).days if pos.buy_date else 0

    def generate_daily_report(self) -> dict:
        """生成每日交易报告"""
        today = date.today().isoformat()

        # 统计今日成交
        today_trades = [t for t in self.orders if t.created_at[:10] == today]
        buy_count = sum(1 for t in today_trades if t.direction == "buy")
        sell_count = sum(1 for t in today_trades if t.direction == "sell")
        buy_amount = sum(t.price * t.volume for t in today_trades if t.direction == "buy")
        sell_amount = sum(t.price * t.volume for t in today_trades if t.direction == "sell")

        # 持仓明细
        holdings = []
        for code, pos in self.positions.items():
            holdings.append({
                "code": pos.code, "name": pos.name,
                "volume": pos.volume, "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": round(pos.market_value, 2),
                "profit_pct": pos.profit_pct,
                "profit_amt": round(pos.profit_amt, 2),
                "holding_days": pos.holding_days,
                "strategy": pos.strategy,
            })

        # 计算日收益率
        today_pnl = round(sum(
            (t.filled_price - t.price) * t.volume * (-1 if t.direction == "sell" else 1)
            for t in today_trades
        ), 2)

        report = {
            "date": today,
            "account": {
                "initial_capital": self.initial_capital,
                "cash": round(self.cash, 2),
                "position_value": round(sum(p.market_value for p in self.positions.values()), 2),
                "total_value": round(self.total_value, 2),
                "total_profit": round(self.total_profit, 2),
                "total_profit_pct": self.total_profit_pct,
                "today_pnl": today_pnl,
            },
            "positions": {
                "count": len(self.positions),
                "holdings": holdings,
            },
            "today_trades": {
                "total": len(today_trades),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "buy_amount": round(buy_amount, 2),
                "sell_amount": round(sell_amount, 2),
                "orders": [
                    {
                        "order_id": t.order_id,
                        "code": t.code, "name": t.name,
                        "direction": t.direction,
                        "price": t.price, "volume": t.volume,
                        "amount": round(t.price * t.volume, 2),
                        "status": t.status,
                        "strategy": t.strategy,
                        "reason": t.reason,
                        "time": t.created_at,
                    }
                    for t in today_trades
                ],
                "sell_orders": [
                    {
                        "code": t.code, "name": t.name,
                        "price": t.filled_price,
                        "volume": t.volume,
                        "reason": t.reason,
                        "time": t.filled_at,
                    }
                    for t in today_trades if t.direction == "sell"
                ],
            },
            "risk_params": {
                "max_positions": self.max_positions,
                "max_position_pct": self.max_position_pct,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
            },
            "generated_at": datetime.now().isoformat(),
        }

        # 持久化报告
        self._save_report(report)
        return report

    def _save_report(self, report: dict):
        """保存报告到数据库"""
        try:
            from app.database import get_connection
            conn = get_connection()
            today = report["date"]
            acc = report["account"]
            conn.execute(
                """INSERT OR REPLACE INTO trade_reports
                   (date, initial_capital, cash, position_value, total_value,
                    total_profit, total_profit_pct, today_pnl, position_count,
                    trade_count, buy_count, sell_count, buy_amount, sell_amount,
                    report_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (today, acc["initial_capital"], acc["cash"], acc["position_value"],
                 acc["total_value"], acc["total_profit"], acc["total_profit_pct"],
                 acc["today_pnl"], report["positions"]["count"],
                 report["today_trades"]["total"], report["today_trades"]["buy_count"],
                 report["today_trades"]["sell_count"], report["today_trades"]["buy_amount"],
                 report["today_trades"]["sell_amount"],
                 json.dumps(report, ensure_ascii=False), datetime.now().isoformat())
            )
        except Exception as e:
            print(f"[交易引擎] 报告保存失败: {e}")

    def save_state(self):
        """保存引擎状态到数据库，重启后恢复"""
        try:
            from app.database import get_connection
            conn = get_connection()
            state = json.dumps({
                "cash": self.cash,
                "order_counter": self.order_counter,
                "start_date": self.start_date,
                "positions": {
                    code: {
                        "code": p.code, "name": p.name, "volume": p.volume,
                        "avg_cost": p.avg_cost, "current_price": p.current_price,
                        "market_value": p.market_value, "buy_date": p.buy_date,
                        "strategy": p.strategy,
                    }
                    for code, p in self.positions.items()
                },
            }, ensure_ascii=False)
            conn.execute(
                "INSERT OR REPLACE INTO kv_store (key, value, updated_at) VALUES ('paper_engine_state', ?, ?)",
                (state, datetime.now().isoformat())
            )
        except Exception as e:
            print(f"[交易引擎] 状态保存失败: {e}")

    def load_state(self):
        """从数据库恢复引擎状态"""
        try:
            from app.database import get_connection
            conn = get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
                )
            """)
            row = conn.execute(
                "SELECT value FROM kv_store WHERE key = 'paper_engine_state'"
            ).fetchone()
            if row:
                state = json.loads(row["value"])
                self.cash = state.get("cash", self.initial_capital)
                self.order_counter = state.get("order_counter", 0)
                self.start_date = state.get("start_date", date.today().isoformat())
                for code, pdata in state.get("positions", {}).items():
                    self.positions[code] = Position(
                        code=pdata["code"], name=pdata["name"],
                        volume=pdata["volume"], avg_cost=pdata["avg_cost"],
                        current_price=pdata.get("current_price", pdata["avg_cost"]),
                        market_value=pdata.get("market_value", 0),
                        buy_date=pdata.get("buy_date", ""),
                        strategy=pdata.get("strategy", ""),
                    )
                print(f"[交易引擎] 状态已恢复: 现金{self.cash:.0f}, 持仓{len(self.positions)}只")
                return True
        except Exception as e:
            print(f"[交易引擎] 状态恢复失败: {e}")
        return False

    def get_status(self, quotes: Dict[str, dict] = None) -> dict:
        """获取当前状态，可选传入实时行情更新持仓"""
        if quotes:
            self.update_positions(quotes)

        return {
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "total_value": round(self.total_value, 2),
            "total_profit": round(self.total_profit, 2),
            "total_profit_pct": self.total_profit_pct,
            "position_count": len(self.positions),
            "today_trade_count": len(self.today_trades),
            "positions": [
                {
                    "code": p.code, "name": p.name, "volume": p.volume,
                    "avg_cost": p.avg_cost, "current_price": p.current_price,
                    "market_value": round(p.market_value, 2),
                    "profit_pct": p.profit_pct, "profit_amt": round(p.profit_amt, 2),
                    "strategy": p.strategy,
                }
                for p in self.positions.values()
            ],
        }


# 全局实例（自动恢复状态）
paper_engine = PaperTradingEngine(initial_capital=100000)
paper_engine.load_state()
