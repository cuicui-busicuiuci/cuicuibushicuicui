'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { runFullScan } from '@/lib/api';

interface ScanResult {
  code: string; name: string; price: number; change_pct: number;
  mcap: number; turnover_pct: number; pe_ttm?: number; pb?: number;
  tech_score?: number; tech_signals?: string[];
  signals: Array<{ strategy: string; confidence: number; reason: string }>;
  signal_count: number; avg_confidence: number; composite_score: number;
  strategies: string[];
}

const STRATEGY_NAMES: Record<string, string> = {
  leader: '龙头', first_board: '首板', second_board: '二板',
  leader_dip: '低吸', main_wave: '主升', money_flow: '资金', weak_to_strong: '弱转强',
};

function getScoreColor(score: number) {
  if (score >= 80) return 'bg-red-500/15 text-red-600';
  if (score >= 60) return 'bg-orange-100 text-orange-400';
  if (score >= 40) return 'bg-yellow-500/15 text-yellow-600';
  return 'bg-[#0F172A] text-slate-300';
}

export default function ScanPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [scanning, setScanning] = useState(false);
  const [scanInfo, setScanInfo] = useState<{total: number; time: number} | null>(null);
  const [error, setError] = useState('');
  const [sortKey, setSortKey] = useState('composite_score');
  const [filterStrategy, setFilterStrategy] = useState('all');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  const startScan = useCallback(async (limit: number) => {
    setScanning(true);
    setError('');
    setResults([]);
    setScanInfo(null);
    try {
      const res = await runFullScan(limit, 40);
      if (res.code === 0) {
        const d = res.data;
        setResults(d.results || []);
        setScanInfo({ total: d.total_scanned, time: d.scan_time_seconds });
      } else {
        setError(res.message || '扫描失败');
      }
    } catch (e: any) {
      setError(e.message || '网络错误');
    } finally {
      setScanning(false);
    }
  }, []);

  const filtered = results
    .filter(r => filterStrategy === 'all' || r.strategies?.includes(filterStrategy))
    .sort((a, b) => {
      const aVal = (a as any)[sortKey] || 0;
      const bVal = (b as any)[sortKey] || 0;
      return bVal - aVal;
    });

  return (
    <div className="min-h-screen bg-[#020617] p-2 md:p-4">
      <div className="flex items-center gap-2 mb-3">
        <Link href="/" className="text-blue-400 text-sm">← 返回</Link>
        <h1 className="text-lg md:text-2xl font-bold">全A实时扫描</h1>
      </div>

      {/* Controls */}
      <div className="bg-[#1E293B] rounded-lg shadow p-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => startScan(100)} disabled={scanning}
            className={`px-3 py-2 rounded-lg font-bold text-white text-sm ${scanning ? 'bg-gray-400' : 'bg-blue-500/100 active:bg-blue-600'}`}>
            {scanning ? '扫描中...' : '快速扫描(100只)'}
          </button>
          <button onClick={() => startScan(0)} disabled={scanning}
            className={`px-3 py-2 rounded-lg font-bold text-white text-sm ${scanning ? 'bg-gray-400' : 'bg-red-500/100 active:bg-red-600'}`}>
            {scanning ? '扫描中...' : '全量扫描(5500只)'}
          </button>

          {scanning && (
            <div className="flex items-center gap-2">
              <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
              <span className="text-sm text-slate-300">扫描中，请等待1-3分钟...</span>
            </div>
          )}

          {scanInfo && (
            <span className="text-xs text-slate-400">
              扫描{scanInfo.total}只，耗时{scanInfo.time}s，入选{results.length}只
            </span>
          )}

          {error && (
            <span className="text-xs text-red-400">{error}</span>
          )}

          {results.length > 0 && (
            <div className="flex flex-wrap gap-2 w-full md:w-auto mt-2 md:mt-0">
              <select value={sortKey} onChange={e => setSortKey(e.target.value)}
                className="border rounded px-2 py-1 text-xs">
                <option value="composite_score">综合评分</option>
                <option value="avg_confidence">信心度</option>
                <option value="signal_count">信号数</option>
                <option value="change_pct">涨跌幅</option>
              </select>
              <select value={filterStrategy} onChange={e => setFilterStrategy(e.target.value)}
                className="border rounded px-2 py-1 text-xs">
                <option value="all">全部策略</option>
                {Object.entries(STRATEGY_NAMES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <button onClick={() => setViewMode(viewMode === 'cards' ? 'table' : 'cards')}
                className="border rounded px-2 py-1 text-xs text-slate-300">
                {viewMode === 'cards' ? '表格' : '卡片'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {viewMode === 'cards' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {filtered.slice(0, 60).map((r, i) => (
            <div key={r.code} className="border rounded-lg p-3 bg-[#1E293B] hover:shadow-md">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">#{i + 1}</span>
                  <span className="font-mono font-bold">{r.code}</span>
                  <span className="font-bold text-sm">{r.name}</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${getScoreColor(r.composite_score)}`}>
                  {r.composite_score}分
                </span>
              </div>
              <div className="grid grid-cols-4 gap-2 text-xs mb-2">
                <div><span className="text-slate-500">价格</span><div className="font-bold">{r.price?.toFixed(2)}</div></div>
                <div><span className="text-slate-500">涨跌</span><div className={`font-bold ${r.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>{r.change_pct > 0 ? '+' : ''}{r.change_pct?.toFixed(1)}%</div></div>
                <div><span className="text-slate-500">换手</span><div className="font-bold">{r.turnover_pct?.toFixed(1)}%</div></div>
                <div><span className="text-slate-500">市值</span><div className="font-bold">{r.mcap?.toFixed(0)}亿</div></div>
              </div>
              <div className="flex flex-wrap gap-1 mb-1">
                {r.strategies?.map(s => (
                  <span key={s} className="px-1.5 py-0.5 bg-blue-500/15 text-blue-400 rounded text-xs">{STRATEGY_NAMES[s] || s}</span>
                ))}
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400 truncate max-w-[70%]">{r.signals?.[0]?.reason?.substring(0, 30)}</span>
                {r.tech_score !== undefined && (
                  <span className={`px-1.5 py-0.5 rounded font-bold ${r.tech_score >= 70 ? 'bg-purple-500/15 text-purple-400' : 'bg-[#0F172A] text-slate-400'}`}>技术{r.tech_score}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-[#1E293B] rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
            <table className="w-full text-xs md:text-sm">
              <thead>
                <tr className="bg-[#020617] border-b">
                  <th className="text-left py-2 px-2">#</th>
                  <th className="text-left py-2 px-2">代码</th>
                  <th className="text-left py-2 px-2">名称</th>
                  <th className="text-right py-2 px-2">价格</th>
                  <th className="text-right py-2 px-2">涨跌</th>
                  <th className="text-right py-2 px-2 hidden md:table-cell">换手</th>
                  <th className="text-right py-2 px-2">评分</th>
                  <th className="text-left py-2 px-2 hidden md:table-cell">策略</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 100).map((r, i) => (
                  <tr key={r.code} className="border-b hover:bg-blue-500/100/10">
                    <td className="py-1.5 px-2 text-slate-500">{i + 1}</td>
                    <td className="py-1.5 px-2 font-mono">{r.code}</td>
                    <td className="py-1.5 px-2 font-bold">{r.name}</td>
                    <td className="py-1.5 px-2 text-right">{r.price?.toFixed(2)}</td>
                    <td className={`py-1.5 px-2 text-right font-bold ${r.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                      {r.change_pct > 0 ? '+' : ''}{r.change_pct?.toFixed(1)}%
                    </td>
                    <td className="py-1.5 px-2 text-right hidden md:table-cell">{r.turnover_pct?.toFixed(1)}%</td>
                    <td className="py-1.5 px-2 text-right">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${getScoreColor(r.composite_score)}`}>{r.composite_score}</span>
                    </td>
                    <td className="py-1.5 px-2 hidden md:table-cell">
                      <div className="flex flex-wrap gap-0.5">
                        {r.strategies?.slice(0, 2).map(s => (
                          <span key={s} className="px-1 py-0.5 bg-blue-500/15 text-blue-400 rounded text-xs">{STRATEGY_NAMES[s] || s}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!scanning && results.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <div className="text-4xl mb-3">📊</div>
          <div className="text-base mb-1">选择扫描模式</div>
          <div className="text-xs mb-3">
            <span className="bg-blue-500/10 px-2 py-1 rounded">快速扫描</span> 扫描前100只 (~40秒)
            <span className="mx-2">|</span>
            <span className="bg-red-500/10 px-2 py-1 rounded">全量扫描</span> 扫描5500只 (~2分钟)
          </div>
          {error && <div className="text-red-400 text-sm">{error}</div>}
        </div>
      )}
    </div>
  );
}
