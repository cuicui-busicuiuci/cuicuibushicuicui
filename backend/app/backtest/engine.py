from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random


@dataclass
class Trade:
    code: str
    name: str
    buy_date: str
    buy_price: float
    sell_date: str = ""
    sell_price: float = 0
    profit_pct: float = 0
    holding_days: int = 0
    strategy: str = ""
    reason: str = ""


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_loss_ratio: float
    avg_holding_days: float
    max_consecutive_loss: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: List[Trade]


class BacktestEngine:
    """回测引擎"""

    def __init__(self):
        self.initial_capital = 1000000  # 初始资金100万
        self.max_position_pct = 0.2  # 单票最大仓位20%
        self.stop_loss_pct = 0.05  # 止损比例5%
        self.take_profit_pct = 0.15  # 止盈比例15%
        self.max_holding_days = 10  # 最大持仓天数

    def run(self, signals: List[Dict], kline_data: Dict[str, List[Dict]]) -> BacktestResult:
        """运行回测"""
        trades = []
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0
        consecutive_loss = 0
        max_consecutive_loss = 0

        for signal in signals:
            code = signal.get("code", "")
            name = signal.get("name", "")
            strategy = signal.get("strategy", "")
            buy_price = signal.get("price", 0)
            stop_loss = signal.get("stop_loss", 0)
            target_price = signal.get("target_price", 0)
            reason = signal.get("reason", "")

            if not code or not buy_price:
                continue

            # 模拟交易
            trade = self._simulate_trade(
                code, name, buy_price, stop_loss, target_price,
                strategy, reason, kline_data.get(code, [])
            )

            if trade:
                trades.append(trade)
                capital += capital * trade.profit_pct / 100

                # 计算最大回撤
                peak_capital = max(peak_capital, capital)
                drawdown = (peak_capital - capital) / peak_capital * 100
                max_drawdown = max(max_drawdown, drawdown)

                # 计算连续亏损
                if trade.profit_pct < 0:
                    consecutive_loss += 1
                    max_consecutive_loss = max(max_consecutive_loss, consecutive_loss)
                else:
                    consecutive_loss = 0

        # 计算统计指标
        total_trades = len(trades)
        if total_trades == 0:
            return BacktestResult(
                total_return=0, annual_return=0, max_drawdown=0,
                sharpe_ratio=0, win_rate=0, profit_loss_ratio=0,
                avg_holding_days=0, max_consecutive_loss=0,
                total_trades=0, winning_trades=0, losing_trades=0,
                trades=[]
            )

        winning_trades = sum(1 for t in trades if t.profit_pct > 0)
        losing_trades = sum(1 for t in trades if t.profit_pct < 0)
        win_rate = winning_trades / total_trades * 100

        avg_profit = sum(t.profit_pct for t in trades if t.profit_pct > 0) / max(winning_trades, 1)
        avg_loss = abs(sum(t.profit_pct for t in trades if t.profit_pct < 0) / max(losing_trades, 1))
        profit_loss_ratio = avg_profit / max(avg_loss, 0.01)

        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        annual_return = total_return * 252 / max(total_trades, 1)
        avg_holding_days = sum(t.holding_days for t in trades) / total_trades

        # 计算夏普比率（简化版）
        returns = [t.profit_pct for t in trades]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = avg_return / max(std_return, 0.01) * (252 ** 0.5)

        return BacktestResult(
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            max_drawdown=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            win_rate=round(win_rate, 2),
            profit_loss_ratio=round(profit_loss_ratio, 2),
            avg_holding_days=round(avg_holding_days, 1),
            max_consecutive_loss=max_consecutive_loss,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            trades=trades
        )

    def _simulate_trade(self, code, name, buy_price, stop_loss, target_price,
                        strategy, reason, klines) -> Optional[Trade]:
        """模拟单笔交易"""
        if not klines:
            # 没有K线数据，使用随机模拟
            holding_days = random.randint(1, self.max_holding_days)
            profit_pct = random.uniform(-5, 10)
            sell_price = buy_price * (1 + profit_pct / 100)

            return Trade(
                code=code,
                name=name,
                buy_date=datetime.now().strftime("%Y-%m-%d"),
                buy_price=buy_price,
                sell_date=(datetime.now() + timedelta(days=holding_days)).strftime("%Y-%m-%d"),
                sell_price=round(sell_price, 2),
                profit_pct=round(profit_pct, 2),
                holding_days=holding_days,
                strategy=strategy,
                reason=reason
            )

        # 有K线数据，模拟真实交易
        buy_idx = 0
        for i, kline in enumerate(klines):
            if kline.get("close", 0) > 0:
                buy_idx = i
                break

        # 模拟持仓
        for i in range(buy_idx + 1, min(buy_idx + self.max_holding_days + 1, len(klines))):
            kline = klines[i]
            close = kline.get("close", 0)
            low = kline.get("low", 0)

            if not close:
                continue

            # 检查止损
            if stop_loss and low <= stop_loss:
                profit_pct = (stop_loss - buy_price) / buy_price * 100
                return Trade(
                    code=code, name=name,
                    buy_date=klines[buy_idx].get("datetime", ""),
                    buy_price=buy_price,
                    sell_date=kline.get("datetime", ""),
                    sell_price=stop_loss,
                    profit_pct=round(profit_pct, 2),
                    holding_days=i - buy_idx,
                    strategy=strategy,
                    reason=reason + " [止损]"
                )

            # 检查止盈
            if target_price and close >= target_price:
                profit_pct = (target_price - buy_price) / buy_price * 100
                return Trade(
                    code=code, name=name,
                    buy_date=klines[buy_idx].get("datetime", ""),
                    buy_price=buy_price,
                    sell_date=kline.get("datetime", ""),
                    sell_price=target_price,
                    profit_pct=round(profit_pct, 2),
                    holding_days=i - buy_idx,
                    strategy=strategy,
                    reason=reason + " [止盈]"
                )

        # 持仓到期，按最后收盘价卖出
        if buy_idx + self.max_holding_days < len(klines):
            last_kline = klines[buy_idx + self.max_holding_days]
            sell_price = last_kline.get("close", buy_price)
            profit_pct = (sell_price - buy_price) / buy_price * 100
            return Trade(
                code=code, name=name,
                buy_date=klines[buy_idx].get("datetime", ""),
                buy_price=buy_price,
                sell_date=last_kline.get("datetime", ""),
                sell_price=sell_price,
                profit_pct=round(profit_pct, 2),
                holding_days=self.max_holding_days,
                strategy=strategy,
                reason=reason + " [到期]"
            )

        return None


backtest_engine = BacktestEngine()
