'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchApi } from '@/lib/api';

interface ScanSession {
  id: number;
  started_at: string;
  total_scanned: number;
  results_count: number;
  scan_time_sec: number;
}

interface ScanItem {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  composite_score: number;
  tech_score: number;
  strategies: string[];
  signal_count: number;
}

interface Dashboard {
  today: { picks: number; signals: number };
  latest_scan: ScanSession | null;
  signal_trend: Array<{ date: string; cnt: number; avg_conf: number }>;
  strategy_distribution: Array<{ strategy: string; cnt: number }>;
}

interface DailyPick {
  code: string;
  name: string;
  level: string;
  confidence: number;
  reason: string;
  risk: string;
}

const STRATEGY_NAMES: Record<string, string> = {
  leader: '龙头', first_board: '首板', second_board: '二板',
  leader_dip: '低吸', main_wave: '主升', money_flow: '资金', weak_to_strong: '弱转强',
};

export default function HistoryPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [scans, setScans] = useState<ScanSession[]>([]);
  const [scanItems, setScanItems] = useState<ScanItem[]>([]);
  const [picks, setPicks] = useState<DailyPick[]>([]);
  const [selectedScan, setSelectedScan] = useState<number | null>(null);
  const [stockCode, setStockCode] = useState('');
  const [stockHistory, setStockHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'dashboard' | 'scans' | 'picks' | 'stock'>('dashboard');

  useEffect(() => { loadDashboard(); loadScans(); }, []);

  async function loadDashboard() {
    try {
      const res = await fetchApi('/api/history/dashboard');
      setDashboard(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function loadScans() {
    try {
      const res = await fetchApi('/api/history/scans?limit=10');
      setScans(res.data || []);
    } catch (e) {}
  }

  async function loadScanDetail(sessionId: number) {
    setSelectedScan(sessionId);
    try {
      const res = await fetchApi(`/api/history/scans/${sessionId}?limit=30`);
      setScanItems(res.data || []);
    } catch (e) {}
  }

  async function loadPicks() {
    setTab('picks');
    try {
      const res = await fetchApi('/api/history/picks');
      setPicks(res.data || []);
    } catch (e) {}
  }

  async function searchStock() {
    if (!stockCode) return;
    setTab('stock');
    try {
      const res = await fetchApi(`/api/history/stock/${stockCode}?limit=20`);
      setStockHistory(res.data || []);
    } catch (e) {}
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-[#020617]">
      <div className="text-xl">加载中...</div>
    </div>;
  }

  return (
    <div className="min-h-screen bg-[#020617] p-2 md:p-4">
      <div className="flex items-center gap-2 mb-3">
        <Link href="/" className="text-blue-400 text-sm">← 返回</Link>
        <h1 className="text-lg md:text-2xl font-bold">历史数据中心</h1>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-3">
        {[
          { k: 'dashboard', n: '概览' },
          { k: 'scans', n: '扫描记录' },
          { k: 'picks', n: '历史推荐' },
          { k: 'stock', n: '个股查询' },
        ].map(t => (
          <button key={t.k}
            onClick={() => { setTab(t.k as any); if (t.k === 'picks') loadPicks(); }}
            className={`px-3 py-1.5 rounded text-sm font-bold ${tab === t.k ? 'bg-blue-500/100 text-white' : 'bg-[#1E293B] text-slate-300 border'}`}
          >{t.n}</button>
        ))}
      </div>

      {/* Dashboard Tab */}
      {tab === 'dashboard' && dashboard && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="bg-[#1E293B] rounded-lg shadow p-3 text-center">
              <div className="text-xs text-slate-400">今日推荐</div>
              <div className="text-2xl font-bold text-blue-400">{dashboard.today.picks}</div>
            </div>
            <div className="bg-[#1E293B] rounded-lg shadow p-3 text-center">
              <div className="text-xs text-slate-400">今日信号</div>
              <div className="text-2xl font-bold text-red-600">{dashboard.today.signals}</div>
            </div>
            <div className="bg-[#1E293B] rounded-lg shadow p-3 text-center">
              <div className="text-xs text-slate-400">最近扫描</div>
              <div className="text-base font-bold">
                {dashboard.latest_scan ? `#${dashboard.latest_scan.id} (${dashboard.latest_scan.results_count}只)` : '无'}
              </div>
            </div>
            <div className="bg-[#1E293B] rounded-lg shadow p-3 text-center">
              <div className="text-xs text-slate-400">扫描耗时</div>
              <div className="text-base font-bold">{dashboard.latest_scan?.scan_time_sec || 0}s</div>
            </div>
          </div>

          {/* Strategy Distribution */}
          <div className="bg-[#1E293B] rounded-lg shadow p-3">
            <h2 className="font-bold text-sm mb-2">策略信号分布(近7天)</h2>
            <div className="flex flex-wrap gap-2">
              {dashboard.strategy_distribution.map((s: any) => (
                <div key={s.strategy} className="px-2 py-1 bg-blue-500/10 rounded text-xs">
                  {STRATEGY_NAMES[s.strategy] || s.strategy}: {s.cnt}次
                </div>
              ))}
              {dashboard.strategy_distribution.length === 0 && (
                <span className="text-xs text-slate-500">暂无数据</span>
              )}
            </div>
          </div>

          {/* Signal Trend */}
          <div className="bg-[#1E293B] rounded-lg shadow p-3">
            <h2 className="font-bold text-sm mb-2">信号趋势(近7天)</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-1">日期</th>
                    <th className="text-right py-1">信号数</th>
                    <th className="text-right py-1">平均信心</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.signal_trend.map((s: any, i: number) => (
                    <tr key={i} className="border-b">
                      <td className="py-1">{s.date}</td>
                      <td className="text-right py-1 font-bold">{s.cnt}</td>
                      <td className="text-right py-1">{s.avg_conf?.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Scans Tab */}
      {tab === 'scans' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[#1E293B] rounded-lg shadow p-3">
            <h2 className="font-bold text-sm mb-2">扫描记录</h2>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {scans.map(s => (
                <div key={s.id}
                  onClick={() => loadScanDetail(s.id)}
                  className={`p-2 rounded cursor-pointer text-sm ${selectedScan === s.id ? 'bg-blue-500/15' : 'hover:bg-[#0F172A]'}`}>
                  <div className="flex justify-between">
                    <span className="font-bold">#{s.id}</span>
                    <span className="text-xs text-slate-400">{s.started_at?.substring(0, 19)}</span>
                  </div>
                  <div className="text-xs text-slate-400">
                    {s.results_count}只 | {s.scan_time_sec}s | 扫描{s.total_scanned}只
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#1E293B] rounded-lg shadow p-3">
            <h2 className="font-bold text-sm mb-2">
              {selectedScan ? `扫描 #${selectedScan} 详情` : '选择左侧扫描'}
            </h2>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {scanItems.map((r, i) => (
                <div key={i} className="border rounded p-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="font-bold">{r.code} {r.name}</span>
                    <span className="text-blue-400 font-bold">{r.composite_score}分</span>
                  </div>
                  <div className="flex justify-between text-slate-400 mt-0.5">
                    <span>技术{r.tech_score} | 信号{r.signal_count}</span>
                    <span className={r.change_pct > 0 ? 'text-red-400' : 'text-green-400'}>
                      {r.change_pct > 0 ? '+' : ''}{r.change_pct?.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Picks Tab */}
      {tab === 'picks' && (
        <div className="bg-[#1E293B] rounded-lg shadow p-3">
          <h2 className="font-bold text-sm mb-2">历史推荐 ({picks.length}只)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {picks.map((p, i) => (
              <div key={i} className="border rounded p-2 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold">{p.code} {p.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                    p.level === '强推荐' ? 'bg-red-500/15 text-red-600' : 'bg-yellow-500/15 text-yellow-600'
                  }`}>{p.level}</span>
                </div>
                <div className="text-slate-300 mb-1 line-clamp-2">{p.reason}</div>
                <div className="flex justify-between text-slate-500">
                  <span>{p.risk?.substring(0, 20)}</span>
                  <span>信心{p.confidence}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stock Search Tab */}
      {tab === 'stock' && (
        <div>
          <div className="flex gap-2 mb-3">
            <input
              type="text" value={stockCode} onChange={e => setStockCode(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && searchStock()}
              placeholder="输入6位股票代码..."
              className="border rounded px-3 py-2 text-sm flex-1 max-w-[200px]"
            />
            <button onClick={searchStock}
              className="bg-blue-500/100 text-white px-4 py-2 rounded text-sm font-bold">
              查询
            </button>
          </div>
          <div className="bg-[#1E293B] rounded-lg shadow p-3">
            <h2 className="font-bold text-sm mb-2">
              {stockCode ? `${stockCode} 历史记录 (${stockHistory.length}条)` : '输入代码查询'}
            </h2>
            <div className="space-y-1">
              {stockHistory.map((h: any, i: number) => (
                <div key={i} className="border rounded p-2 text-xs">
                  <div className="flex justify-between">
                    <span className="font-bold">综合{h.composite_score} | 技术{h.tech_score}</span>
                    <span className="text-slate-400">{h.scan_time?.substring(0, 19)}</span>
                  </div>
                  <div className="text-slate-400">
                    价格{h.price} | 涨跌{h.change_pct?.toFixed(1)}% | 换手{h.turnover_pct?.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
