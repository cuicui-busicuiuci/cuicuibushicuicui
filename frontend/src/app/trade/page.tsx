'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { fetchApi, postApi, getTradeStatus, startAutoTrader, stopAutoTrader, getAutoTraderStatus, createTradeStreamUrl } from '@/lib/api';

interface TradeStatus {
  initial_capital: number; cash: number; total_value: number;
  total_profit: number; total_profit_pct: number;
  position_count: number; today_trade_count: number;
  positions: Array<{
    code: string; name: string; volume: number;
    avg_cost: number; current_price: number;
    market_value: number; profit_pct: number; profit_amt: number;
    strategy: string;
  }>;
}

interface AutoTraderStatus {
  is_running: boolean; interval: number;
  last_run: string | null; last_error: string;
  cycles: number; trades_today: number;
  signals_last: number; orders_last: number;
}

export default function TradePage() {
  const [status, setStatus] = useState<TradeStatus | null>(null);
  const [autoStatus, setAutoStatus] = useState<AutoTraderStatus | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [tradeEvents, setTradeEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'status' | 'history' | 'events'>('status');
  const [trading, setTrading] = useState(false);
  const [autoLoading, setAutoLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // SSE 实时流
  useEffect(() => {
    const url = createTradeStreamUrl();
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        switch (msg.event) {
          case 'init':
            if (msg.data.status) setStatus(msg.data.status);
            if (msg.data.auto_trader) setAutoStatus(msg.data.auto_trader);
            break;
          case 'status':
            setStatus(msg.data);
            break;
          case 'trade':
            setTradeEvents(prev => [...msg.data.orders, ...prev].slice(0, 50));
            loadStatus();
            break;
          case 'cycle':
            setAutoStatus(msg.data);
            break;
        }
      } catch {}
    };

    es.onerror = () => { /* 自动重连 */ };

    return () => { es.close(); };
  }, []);

  // 初始加载
  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [sRes, hRes, aRes] = await Promise.all([
        getTradeStatus(),
        fetchApi('/api/trade/reports?limit=7'),
        getAutoTraderStatus(),
      ]);
      setStatus(sRes.data);
      setHistory(hRes.data || []);
      setAutoStatus(aRes.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function loadStatus() {
    try { const r = await getTradeStatus(); setStatus(r.data); } catch {}
  }

  async function runTrading() {
    setTrading(true);
    try {
      const res = await postApi('/api/trade/run');
      if (res.code === 0) { setStatus(res.data.status); alert('成交' + res.data.orders_executed + '笔'); loadData(); }
    } catch (e: any) { alert('执行失败: ' + e.message); }
    finally { setTrading(false); }
  }

  async function handleAutoStart() {
    setAutoLoading(true);
    try { await startAutoTrader(); await loadData(); } catch (e: any) { alert('启动失败: ' + e.message); }
    finally { setAutoLoading(false); }
  }

  async function handleAutoStop() {
    setAutoLoading(true);
    try { await stopAutoTrader(); await loadData(); } catch (e: any) { alert('停止失败: ' + e.message); }
    finally { setAutoLoading(false); }
  }

  async function loadReport() {
    try {
      const res = await postApi('/api/trade/report');
      setTab('status');
      alert('报告已生成');
    } catch (e: any) { alert('失败: ' + e.message); }
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-[#020617]"><div className="text-slate-400">加载中...</div></div>;

  return (
    <div className="min-h-screen bg-[#020617] p-2 md:p-4">
      <div className="flex items-center gap-2 mb-3">
        <Link href="/" className="text-blue-400 text-sm">← 返回</Link>
        <h1 className="text-lg md:text-2xl font-bold">模拟交易</h1>
        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded font-mono">100,000</span>
      </div>

      {/* 自动交易引擎状态 */}
      {autoStatus && (
        <div className={`card p-3 mb-3 border ${autoStatus.is_running ? 'border-green-500/30' : 'border-slate-700/50'}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${autoStatus.is_running ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
              <span className="font-bold text-sm">
                {autoStatus.is_running ? '自动交易运行中' : '自动交易已停止'}
              </span>
              {autoStatus.is_running && (
                <span className="text-xs text-slate-500">
                  间隔{autoStatus.interval}s | 周期{autoStatus.cycles} | 今日成交{autoStatus.trades_today}笔
                </span>
              )}
            </div>
            <div className="flex gap-2">
              {autoStatus.is_running ? (
                <button onClick={handleAutoStop} disabled={autoLoading}
                  className="px-3 py-1 rounded bg-red-600 text-white text-xs hover:bg-red-500 disabled:opacity-50">
                  停止
                </button>
              ) : (
                <button onClick={handleAutoStart} disabled={autoLoading}
                  className="px-3 py-1 rounded bg-green-600 text-white text-xs hover:bg-green-500 disabled:opacity-50">
                  启动
                </button>
              )}
            </div>
          </div>
          {autoStatus.last_error && <div className="text-xs text-red-400 mt-1">错误: {autoStatus.last_error}</div>}
        </div>
      )}

      {/* 账户概览 */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
          {[
            { l: '总资产', v: status.total_value?.toLocaleString(), c: 'text-blue-400' },
            { l: '总盈亏', v: `${status.total_profit>=0?'+':''}${status.total_profit?.toLocaleString()}`, c: status.total_profit>=0?'text-red-400':'text-green-400', sub: `${status.total_profit_pct>=0?'+':''}${status.total_profit_pct}%` },
            { l: '现金', v: status.cash?.toLocaleString(), c: 'text-slate-300' },
            { l: '持仓', v: `${status.position_count}只`, c: 'text-yellow-400' },
          ].map((c, i) => (
            <div key={i} className="card p-3 text-center">
              <div className="text-xs text-slate-500">{c.l}</div>
              <div className={`text-lg font-bold ${c.c}`}>{c.v}</div>
              {c.sub && <div className="text-xs text-slate-500">{c.sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* 标签页 */}
      <div className="flex flex-wrap gap-2 mb-3">
        <button onClick={runTrading} disabled={trading}
          className={`px-4 py-2 rounded-lg font-bold text-sm ${trading ? 'bg-slate-700 text-slate-400' : 'bg-green-600 text-white hover:bg-green-500'}`}>
          {trading ? '执行中...' : '手动交易'}
        </button>
        <button onClick={loadReport} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-bold hover:bg-blue-500">生成报告</button>
        {[
          { key: 'status', label: '持仓' },
          { key: 'events', label: `实时(${tradeEvents.length})` },
          { key: 'history', label: '历史' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className={`px-3 py-2 rounded-lg text-sm ${tab===t.key ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 border border-slate-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* 持仓 */}
      {tab === 'status' && status && (
        <div className="card p-3">
          <h2 className="font-bold text-sm mb-2">持仓 ({status.positions.length}只)</h2>
          {status.positions.length === 0 ? (
            <div className="text-center text-slate-500 py-8 text-sm">暂无持仓，点击"手动交易"或启动自动交易</div>
          ) : (
            <div className="space-y-2">
              {status.positions.map((p, i) => (
                <div key={i} className="border border-slate-700/50 rounded-lg p-2 text-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold data-font">{p.code}</span>
                    <span className="text-slate-400">{p.name}</span>
                    <span className={`font-bold ${p.profit_pct>=0?'text-red-400':'text-green-400'}`}>{p.profit_pct>=0?'+':''}{p.profit_pct}%</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-slate-500">
                    <div>成本 {p.avg_cost.toFixed(2)}</div>
                    <div>现价 {p.current_price.toFixed(2)}</div>
                    <div>市值 {p.market_value.toLocaleString()}</div>
                    <div>盈亏 <span className={p.profit_amt>=0?'text-red-400':'text-green-400'}>{p.profit_amt>=0?'+':''}{p.profit_amt.toFixed(0)}</span></div>
                  </div>
                  <div className="text-slate-600 mt-0.5">{p.strategy} | {p.volume}股</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 实时成交事件 */}
      {tab === 'events' && (
        <div className="card p-3">
          <h2 className="font-bold text-sm mb-2">实时成交记录</h2>
          {tradeEvents.length === 0 ? (
            <div className="text-center text-slate-500 py-8 text-sm">等待成交事件...</div>
          ) : (
            <div className="space-y-1 max-h-[60vh] overflow-y-auto">
              {tradeEvents.map((evt: any, i: number) => (
                <div key={i} className={`border rounded p-2 text-xs flex items-center gap-2 ${evt.direction === 'buy' ? 'border-red-500/20 bg-red-500/5' : 'border-green-500/20 bg-green-500/5'}`}>
                  <span className={`font-bold ${evt.direction === 'buy' ? 'text-red-400' : 'text-green-400'}`}>
                    {evt.direction === 'buy' ? '买入' : '卖出'}
                  </span>
                  <span className="data-font">{evt.code}</span>
                  <span className="text-slate-400">{evt.name}</span>
                  <span className="text-slate-300">{evt.price}元</span>
                  <span className="text-slate-500">{evt.volume}股</span>
                  <span className="text-slate-500 bg-slate-800 px-1 rounded">{evt.strategy}</span>
                  <span className="text-slate-600 truncate max-w-[150px]">{evt.reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 历史 */}
      {tab === 'history' && (
        <div className="card p-3">
          <h2 className="font-bold text-sm mb-2">历史报告</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-slate-700">
                {['日期','总资产','盈亏','收益率','日盈亏','持仓','成交'].map(h=><th key={h} className="text-left py-2 px-1 text-slate-500">{h}</th>)}
              </tr></thead>
              <tbody>
                {history.map((h: any, i: number) => (
                  <tr key={i} className="border-b border-slate-800">
                    <td className="py-1.5 px-1 data-font">{h.date}</td>
                    <td className="py-1.5 px-1">{h.total_value?.toLocaleString()}</td>
                    <td className={`py-1.5 px-1 font-bold ${h.total_profit>=0?'text-red-400':'text-green-400'}`}>{h.total_profit>=0?'+':''}{h.total_profit?.toLocaleString()}</td>
                    <td className={`py-1.5 px-1 ${h.total_profit_pct>=0?'text-red-400':'text-green-400'}`}>{h.total_profit_pct>=0?'+':''}{h.total_profit_pct}%</td>
                    <td className={`py-1.5 px-1 ${h.today_pnl>=0?'text-red-400':'text-green-400'}`}>{h.today_pnl>=0?'+':''}{h.today_pnl?.toLocaleString()}</td>
                    <td className="py-1.5 px-1">{h.position_count}</td>
                    <td className="py-1.5 px-1">{h.trade_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
