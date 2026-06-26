'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { runFullScan, getAiBuyReason, getRiskTips } from '@/lib/api';

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
  const [detailStock, setDetailStock] = useState<{code: string; name: string} | null>(null);
  const [aiReason, setAiReason] = useState<any>(null);
  const [riskTips, setRiskTips] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

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

  const openDetail = useCallback(async (code: string, name: string) => {
    setDetailStock({ code, name });
    setDetailLoading(true);
    setAiReason(null);
    setRiskTips(null);
    try {
      const [reasonRes, riskRes] = await Promise.all([
        getAiBuyReason(code),
        getRiskTips(code),
      ]);
      if (reasonRes.code === 0) setAiReason(reasonRes.data);
      if (riskRes.code === 0) setRiskTips(riskRes.data);
    } catch (e) { console.error(e); }
    finally { setDetailLoading(false); }
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
            <div key={r.code} onClick={() => openDetail(r.code, r.name)}
              className="border rounded-lg p-3 bg-[#1E293B] hover:shadow-md cursor-pointer hover:border-blue-500/30 transition-colors">
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
                  <tr key={r.code}
                    onClick={() => openDetail(r.code, r.name)}
                    className="border-b hover:bg-blue-500/10 cursor-pointer">
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

      {/* AI分析弹窗 */}
      {detailStock && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setDetailStock(null)}>
          <div className="bg-[#1E293B] border border-slate-600 rounded-xl p-4 w-full max-w-md mx-2 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <div>
                <span className="font-mono font-bold text-lg">{detailStock.code}</span>
                <span className="text-slate-400 ml-2">{detailStock.name}</span>
              </div>
              <button onClick={() => setDetailStock(null)} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
            </div>

            {detailLoading ? (
              <div className="text-center text-slate-400 py-8">
                <div className="inline-block animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-3" />
                <div className="text-sm">AI 正在分析（约15-30秒）...</div>
                <div className="text-xs text-slate-500 mt-1">首次调用较慢，30分钟内重复点击秒回</div>
              </div>
            ) : (
              <div className="space-y-3">
                {/* AI买入原因 */}
                {aiReason && (
                  <div className="card p-3 border border-blue-500/20">
                    <h3 className="font-bold text-sm text-blue-400 mb-2">AI买入原因</h3>
                    <div className="flex gap-2 mb-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded text-xs bg-blue-500/10 text-blue-400">Alpha {aiReason.alpha_score}分</span>
                      {aiReason.tech_score > 0 && <span className="px-2 py-0.5 rounded text-xs bg-purple-500/10 text-purple-400">技术 {aiReason.tech_score}分</span>}
                      {aiReason.main_force_pace && aiReason.main_force_pace !== 'unknown' && (
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          aiReason.main_force_pace === 'pulling' ? 'bg-red-500/15 text-red-400' :
                          aiReason.main_force_pace === 'accumulation' ? 'bg-blue-500/15 text-blue-400' :
                          aiReason.main_force_pace === 'washing' ? 'bg-yellow-500/15 text-yellow-400' :
                          aiReason.main_force_pace === 'distribution' ? 'bg-gray-500/15 text-gray-400' : 'bg-slate-700 text-slate-400'
                        }`}>
                          {aiReason.main_force_pace === 'pulling' ? '拉升' :
                           aiReason.main_force_pace === 'accumulation' ? '建仓' :
                           aiReason.main_force_pace === 'washing' ? '洗盘' :
                           aiReason.main_force_pace === 'distribution' ? '出货' : aiReason.main_force_pace}
                          {aiReason.main_force_strength ? ` ${aiReason.main_force_strength}` : ''}
                        </span>
                      )}
                      {aiReason.board_count > 0 && (
                        <span className="px-2 py-0.5 rounded text-xs bg-orange-500/15 text-orange-400">{aiReason.board_count}板</span>
                      )}
                      {aiReason.sector && (
                        <span className="px-2 py-0.5 rounded text-xs bg-green-500/10 text-green-400">{aiReason.sector}</span>
                      )}
                    </div>
                    {aiReason.pace_desc && aiReason.main_force_pace && aiReason.main_force_pace !== 'unknown' && (
                      <div className="text-xs text-slate-500 mb-1.5">{aiReason.pace_desc}</div>
                    )}
                    <div className="text-sm text-slate-300 font-bold mb-1.5">{aiReason.summary}</div>
                    <ul className="space-y-1">
                      {aiReason.reasons?.map((r: string, i: number) => (
                        <li key={i} className="text-xs text-slate-400 flex items-start gap-1">
                          <span className="text-blue-400 mt-0.5">•</span> {r}
                        </li>
                      ))}
                    </ul>
                    {aiReason.main_net_inflow ? (
                      <div className="mt-2 pt-2 border-t border-slate-700/50 text-xs flex gap-3">
                        <span className={aiReason.main_net_inflow > 0 ? 'text-red-400' : 'text-green-400'}>
                          主力净流入: {(aiReason.main_net_inflow / 1e8).toFixed(2)}亿
                        </span>
                        {aiReason.main_net_5d ? (
                          <span className={aiReason.main_net_5d > 0 ? 'text-red-400' : 'text-green-400'}>
                            5日: {(aiReason.main_net_5d / 1e8).toFixed(2)}亿
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )}

                {/* 风险提示 */}
                {riskTips && (
                  <div className="card p-3 border border-red-500/20">
                    <h3 className="font-bold text-sm text-red-400 mb-2">风险提示</h3>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        riskTips.risk_level === 'HIGH' ? 'bg-red-500/20 text-red-400' :
                        riskTips.risk_level === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'
                      }`}>风险 {riskTips.risk_level}</span>
                      <span className="text-xs text-slate-500">{riskTips.suggestion}</span>
                    </div>
                    {riskTips.risk_factors?.length > 0 && (
                      <ul className="space-y-1">
                        {riskTips.risk_factors.map((r: string, i: number) => (
                          <li key={i} className="text-xs text-slate-400 flex items-start gap-1">
                            <span className="text-red-400 mt-0.5">⚠</span> {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
