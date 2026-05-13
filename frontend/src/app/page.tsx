'use client';

import { useMarketData } from '@/lib/useMarketData';
import Link from 'next/link';

interface Signal {
  code: string; name: string; price: number;
  stop_loss: number; target_price: number;
  reason: string; risk: string; confidence: number;
  level?: string; mcap?: number; turnover_pct?: number; pe_ttm?: number;
}

function ScoreBadge({ score }: { score: number }) {
  let cls = 'px-2 py-0.5 rounded text-xs font-bold ';
  if (score >= 80) cls += 'bg-red-500/20 text-red-400';
  else if (score >= 60) cls += 'bg-orange-500/20 text-orange-400';
  else if (score >= 40) cls += 'bg-yellow-500/20 text-yellow-400';
  else cls += 'bg-slate-500/20 text-slate-400';
  return <span className={cls}>{score}分</span>;
}

function SignalCard({ title, signals, icon }: { title: string; signals: Signal[]; icon: string }) {
  return (
    <div className="card p-4 cursor-pointer">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <h2 className="font-semibold text-sm">{title}</h2>
        <span className="text-xs text-slate-500 ml-auto">{signals.length}只</span>
      </div>
      <div className="space-y-2 max-h-44 overflow-y-auto">
        {signals.length === 0 ? (
          <div className="text-xs text-slate-600 text-center py-4">暂无信号</div>
        ) : signals.slice(0, 3).map((s, i) => (
          <div key={i} className="border-b border-slate-700/50 pb-2 last:border-0">
            <div className="flex justify-between items-center">
              <span className="font-bold text-xs data-font">{s.code}</span>
              <span className="text-xs text-slate-400">{s.name}</span>
              <ScoreBadge score={s.confidence} />
            </div>
            <div className="text-xs text-slate-500 mt-1 truncate">{s.reason?.substring(0, 35)}</div>
            <div className="flex gap-2 mt-1 text-xs">
              <span className="text-red-400">↓{s.stop_loss}</span>
              <span className="text-green-400">↑{s.target_price}</span>
              {(s.mcap || 0) > 0 && <span className="text-slate-600">{((s.mcap||0)>=10000?((s.mcap||0)/10000).toFixed(1)+'万':(s.mcap||0).toFixed(0))}亿</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const STRATEGY_CONFIG: Record<string, { title: string; icon: string }> = {
  leader: { title: '龙头战法', icon: '🐉' },
  first_board: { title: '首板战法', icon: '①' },
  second_board: { title: '换手二板', icon: '②' },
  leader_dip: { title: '龙头低吸', icon: '📉' },
  main_wave: { title: '主升浪', icon: '🌊' },
  money_flow: { title: '资金流', icon: '💰' },
  weak_to_strong: { title: '弱转强', icon: '🔄' },
};

export default function Home() {
  const { data, loading, error, lastUpdate, refresh } = useMarketData();
  const sentiment = data?.sentiment;
  const strategies = data?.strategies || {};
  const recommendations = data?.recommendations || [];
  const totalSignals = data?.total_signals || 0;

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#020617]">
        <div className="text-center">
          {loading ? (
            <>
              <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <div className="text-slate-400">加载数据...</div>
            </>
          ) : error ? (
            <>
              <div className="text-4xl mb-4">!</div>
              <div className="text-red-400 mb-2">加载失败</div>
              <div className="text-xs text-slate-500 mb-4">{error}</div>
              <button onClick={refresh} className="btn-primary">重试</button>
            </>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] p-3 md:p-6">
      {/* Top Bar */}
      <div className="flex flex-wrap justify-between items-center mb-4 gap-2">
        <div>
          <h1 className="text-xl md:text-3xl font-bold">
            <span className="text-green-400">A股</span>量化投研
          </h1>
          <div className="text-xs text-slate-500 mt-0.5">
            {lastUpdate && <span>更新 {lastUpdate}</span>}
            <span className="ml-2 px-2 py-0.5 rounded bg-green-500/10 text-green-400 text-xs">10秒刷新</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs border border-slate-700 hover:border-slate-500 transition-colors">
            刷新
          </button>
        </div>
      </div>

      {/* Nav */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {[
          { href: '/market', label: '行情', color: 'bg-blue-600' },
          { href: '/strategy', label: '策略', color: 'bg-green-600' },
          { href: '/scan', label: '全A扫描', color: 'bg-red-600' },
          { href: '/trade', label: '模拟交易', color: 'bg-orange-600' },
          { href: '/history', label: '历史', color: 'bg-purple-600' },
        ].map(nav => (
          <Link key={nav.href} href={nav.href}
            className={`${nav.color} text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:opacity-90 transition-opacity`}>
            {nav.label}
          </Link>
        ))}
        <div className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-400 text-xs border border-slate-700">
          总信号 {totalSignals}只
        </div>
      </div>

      {/* Sentiment Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        {[
          { label: '市场情绪', value: sentiment?.stage || '-', sub: `分数 ${sentiment?.score || 0}`, color: 'text-blue-400' },
          { label: '涨停', value: `${sentiment?.limit_up_count || 0}只`, sub: '今日', color: 'text-red-400' },
          { label: '最高连板', value: `${sentiment?.max_board || 0}板`, sub: '高度', color: 'text-orange-400' },
          { label: '操作建议', value: sentiment?.action || '-', sub: sentiment?.risk_level || '', color: 'text-green-400' },
        ].map((c, i) => (
          <div key={i} className="card p-3 text-center">
            <div className="text-xs text-slate-500 mb-1">{c.label}</div>
            <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
            <div className="text-xs text-slate-600">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      <div className="card p-4 mb-4">
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-bold text-sm">每日推荐 <span className="text-slate-500 font-normal">({recommendations.length}只)</span></h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {recommendations.slice(0, 8).map((rec: any, i: number) => (
            <div key={i} className="border border-slate-700/50 rounded-lg p-3 hover:border-slate-600 transition-colors">
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-xs data-font">{rec.code}</span>
                <span className="text-xs text-slate-400">{rec.name}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  rec.level === '强推荐' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                }`}>{rec.level}</span>
              </div>
              <div className="text-xs text-slate-500 mb-1 truncate">{rec.reason?.substring(0, 55)}</div>
              <div className="flex justify-between text-xs">
                <span className="text-red-400/70">{rec.risk?.substring(0, 15)}</span>
                <span className="text-slate-600">信心 {rec.confidence}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strategy Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {Object.entries(STRATEGY_CONFIG).map(([key, config]) => (
          <SignalCard key={key} title={config.title} signals={strategies[key] || []} icon={config.icon} />
        ))}
      </div>
    </div>
  );
}
