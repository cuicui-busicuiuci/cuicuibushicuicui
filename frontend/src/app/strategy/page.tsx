'use client';

import { useEffect, useState } from 'react';
import { getLeaderSignals, getFirstBoardSignals, getSecondBoardSignals, getLeaderDipSignals, getMainWaveSignals, getWeakToStrongSignals, getMoneyFlowSignals, getSentiment, getHotStocks, runBacktest } from '@/lib/api';
import Link from 'next/link';

interface Signal {
  code: string;
  name: string;
  strategy: string;
  price: number;
  stop_loss: number;
  target_price: number;
  reason: string;
  risk: string;
  confidence: number;
  mcap?: number;
  turnover_pct?: number;
  pe_ttm?: number;
}

interface Sentiment {
  stage: string;
  score: number;
  limit_up_count: number;
  limit_down_count: number;
  max_board: number;
  first_board_count: number;
  second_board_count: number;
  high_board_count: number;
  profit_effect: number;
  description: string;
  action: string;
  suggested_position: number;
  risk_level: string;
}

interface HotStock {
  code: string;
  name: string;
  reason: string;
  analyse: string;
  change_pct: number;
  hot_score: number;
  concept_tags: string[];
  popularity_tag: string;
}

interface BacktestResult {
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_loss_ratio: number;
  avg_holding_days: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

export default function StrategyPage() {
  const [leaderSignals, setLeaderSignals] = useState<Signal[]>([]);
  const [firstBoardSignals, setFirstBoardSignals] = useState<Signal[]>([]);
  const [secondBoardSignals, setSecondBoardSignals] = useState<Signal[]>([]);
  const [leaderDipSignals, setLeaderDipSignals] = useState<Signal[]>([]);
  const [mainWaveSignals, setMainWaveSignals] = useState<Signal[]>([]);
  const [weakToStrongSignals, setWeakToStrongSignals] = useState<Signal[]>([]);
  const [moneyFlowSignals, setMoneyFlowSignals] = useState<Signal[]>([]);
  const [sentiment, setSentiment] = useState<Sentiment | null>(null);
  const [hotStocks, setHotStocks] = useState<HotStock[]>([]);
  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [activeTab, setActiveTab] = useState('leader');
  const [selectedStock, setSelectedStock] = useState<HotStock | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [leaderRes, firstBoardRes, secondBoardRes, leaderDipRes, mainWaveRes, weakRes, moneyRes, sentimentRes, hotRes] = await Promise.all([
        getLeaderSignals(),
        getFirstBoardSignals(),
        getSecondBoardSignals(),
        getLeaderDipSignals(),
        getMainWaveSignals(),
        getWeakToStrongSignals(),
        getMoneyFlowSignals(),
        getSentiment(),
        getHotStocks(),
      ]);

      setLeaderSignals(leaderRes.data || []);
      setFirstBoardSignals(firstBoardRes.data || []);
      setSecondBoardSignals(secondBoardRes.data || []);
      setLeaderDipSignals(leaderDipRes.data || []);
      setMainWaveSignals(mainWaveRes.data || []);
      setWeakToStrongSignals(weakRes.data || []);
      setMoneyFlowSignals(moneyRes.data || []);
      setSentiment(sentimentRes.data);
      setHotStocks(hotRes.data || []);
    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleBacktest() {
    try {
      const res = await runBacktest();
      setBacktest(res.data);
    } catch (error) {
      console.error('回测失败:', error);
    }
  }

  const getSignals = () => {
    switch (activeTab) {
      case 'leader': return leaderSignals;
      case 'firstboard': return firstBoardSignals;
      case 'secondboard': return secondBoardSignals;
      case 'leaderdip': return leaderDipSignals;
      case 'mainwave': return mainWaveSignals;
      case 'weaktostrong': return weakToStrongSignals;
      case 'moneyflow': return moneyFlowSignals;
      default: return leaderSignals;
    }
  };

  const getStrategyName = () => {
    switch (activeTab) {
      case 'leader': return '龙头战法';
      case 'firstboard': return '首板战法';
      case 'secondboard': return '换手二板';
      case 'leaderdip': return '龙头低吸';
      case 'mainwave': return '主升浪';
      case 'weaktostrong': return '弱转强';
      case 'moneyflow': return '资金流';
      default: return '龙头战法';
    }
  };

  const getStrategyDesc = () => {
    switch (activeTab) {
      case 'leader': return '识别板块龙头股，捕捉主升浪行情。龙头股具有带动效应，涨幅领先，是市场关注焦点。';
      case 'firstboard': return '捕捉首次涨停股票，博取次日溢价。首板股具有较强爆发力，但需注意次日低开风险。';
      case 'secondboard': return '捕捉换手充分的二板股票，博取三板溢价。二板确认龙头地位，换手充分更健康。';
      case 'leaderdip': return '在龙头股回调时低吸，博取二波行情。龙头股回调到位后，有望开启新一轮上涨。';
      case 'mainwave': return '捕捉股票主升浪行情，持股待涨。主升浪是股票上涨最猛烈的阶段。';
      case 'weaktostrong': return '识别弱势转强势的转折信号，捕捉反转行情。通过量价反转、资金回流、翘板等特征发现弱转强机会。';
      case 'moneyflow': return '跟踪主力资金流向，捕捉多路资金合力共振的信号。分析资金流入流出、游资机构联动等指标。';
      default: return '';
    }
  };

  const signals = getSignals();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] p-4 md:p-6">
      <div className="flex items-center mb-6">
        <Link href="/" className="text-blue-400 hover:underline mr-4">← 返回首页</Link>
        <h1 className="text-2xl md:text-3xl font-bold">策略中心</h1>
      </div>

      {/* 市场情绪详情 */}
      <div className="bg-[#1E293B] rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-bold mb-3">市场情绪分析</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-xs text-slate-400">阶段</div>
            <div className="text-xl font-bold text-blue-400">{sentiment?.stage}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">分数</div>
            <div className="text-xl font-bold">{sentiment?.score}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">建议仓位</div>
            <div className="text-xl font-bold text-green-400">{sentiment?.suggested_position}%</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">风险等级</div>
            <div className={`text-xl font-bold ${sentiment?.risk_level === 'HIGH' ? 'text-red-600' : sentiment?.risk_level === 'MEDIUM' ? 'text-yellow-600' : 'text-green-400'}`}>
              {sentiment?.risk_level}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
          <div>
            <div className="text-slate-400">涨停</div>
            <div className="font-bold text-red-600">{sentiment?.limit_up_count}只</div>
          </div>
          <div>
            <div className="text-slate-400">跌停</div>
            <div className="font-bold text-green-400">{sentiment?.limit_down_count}只</div>
          </div>
          <div>
            <div className="text-slate-400">首板</div>
            <div className="font-bold">{sentiment?.first_board_count}只</div>
          </div>
          <div>
            <div className="text-slate-400">二板</div>
            <div className="font-bold">{sentiment?.second_board_count}只</div>
          </div>
          <div>
            <div className="text-slate-400">高标(3板+)</div>
            <div className="font-bold">{sentiment?.high_board_count}只</div>
          </div>
        </div>
        <div className="mt-3 text-sm text-slate-300">
          <span className="font-bold">赚钱效应：</span>{sentiment?.profit_effect} |
          <span className="font-bold ml-2">操作建议：</span>{sentiment?.action}
        </div>
      </div>

      {/* 策略切换 */}
      <div className="bg-[#1E293B] rounded-lg shadow mb-6">
        <div className="flex flex-wrap border-b">
          {[
            { key: 'leader', name: '龙头战法', count: leaderSignals.length },
            { key: 'firstboard', name: '首板战法', count: firstBoardSignals.length },
            { key: 'secondboard', name: '换手二板', count: secondBoardSignals.length },
            { key: 'leaderdip', name: '龙头低吸', count: leaderDipSignals.length },
            { key: 'mainwave', name: '主升浪', count: mainWaveSignals.length },
            { key: 'moneyflow', name: '资金流', count: moneyFlowSignals.length },
            { key: 'weaktostrong', name: '弱转强', count: weakToStrongSignals.length },
          ].map(tab => (
            <button
              key={tab.key}
              className={`px-4 py-3 font-bold text-sm ${activeTab === tab.key ? 'text-blue-400 border-b-2 border-blue-600' : 'text-slate-400'}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.name} ({tab.count})
            </button>
          ))}
        </div>
      </div>

      {/* 策略说明 */}
      <div className="bg-[#1E293B] rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-bold mb-2">{getStrategyName()}</h2>
        <p className="text-sm text-slate-300 mb-3">{getStrategyDesc()}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-slate-400">信号数量</div>
            <div className="font-bold">{signals.length}只</div>
          </div>
          <div>
            <div className="text-slate-400">平均置信度</div>
            <div className="font-bold">{signals.length > 0 ? (signals.reduce((a, b) => a + b.confidence, 0) / signals.length).toFixed(1) : 0}</div>
          </div>
          <div>
            <div className="text-slate-400">最高置信度</div>
            <div className="font-bold">{signals.length > 0 ? Math.max(...signals.map(s => s.confidence)) : 0}</div>
          </div>
          <div>
            <div className="text-slate-400">最低置信度</div>
            <div className="font-bold">{signals.length > 0 ? Math.min(...signals.map(s => s.confidence)) : 0}</div>
          </div>
        </div>
      </div>

      {/* 信号列表 */}
      <div className="bg-[#1E293B] rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-bold mb-3">{getStrategyName()}信号 ({signals.length}只)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {signals.slice(0, 12).map((signal, i) => (
            <div key={i} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="font-bold text-lg">{signal.code}</div>
                  <div className="text-slate-300">{signal.name}</div>
                </div>
                <div className="bg-blue-500/15 text-blue-400 px-2 py-1 rounded text-sm">
                  {signal.confidence}分
                </div>
              </div>
              <div className="text-sm text-slate-300 mb-3">{signal.reason}</div>
              <div className="grid grid-cols-3 gap-2 text-sm mb-2">
                <div>
                  <div className="text-slate-500">买入价</div>
                  <div className="font-bold">{signal.price}</div>
                </div>
                <div>
                  <div className="text-slate-500">止损/目标</div>
                  <div className="font-bold"><span className="text-red-600">{signal.stop_loss}</span>/<span className="text-green-400">{signal.target_price}</span></div>
                </div>
                <div>
                  <div className="text-slate-500">市值/换手</div>
                  <div className="font-bold text-xs">
                    {(signal.mcap||0) > 0 ? (((signal.mcap||0) >= 10000 ? ((signal.mcap||0)/10000).toFixed(1)+'万' : (signal.mcap||0).toFixed(0)+'亿')) : '-'}
                    {(signal.turnover_pct||0) > 0 ? ` / ${(signal.turnover_pct||0).toFixed(1)}%` : ''}
                  </div>
                </div>
              </div>
              <div className="text-xs text-red-400 bg-red-500/10 p-2 rounded">{signal.risk}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 今日热点新闻 */}
      <div className="bg-[#1E293B] rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-bold mb-3">今日热点新闻</h2>
        <div className="space-y-3">
          {hotStocks.slice(0, 8).map((stock, i) => (
            <div key={i} className="border-b pb-3 cursor-pointer hover:bg-[#020617] p-2 rounded"
              onClick={() => setSelectedStock(stock)}>
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-sm">{stock.code} {stock.name}</span>
                <span className={`text-sm font-bold ${stock.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                  {stock.change_pct > 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                </span>
              </div>
              <div className="text-xs text-slate-300 mb-1">{stock.reason}</div>
              <div className="flex flex-wrap gap-1">
                {stock.concept_tags?.slice(0, 3).map((tag, j) => (
                  <span key={j} className="px-2 py-1 bg-blue-500/15 text-blue-400 rounded text-xs">{tag}</span>
                ))}
                {stock.popularity_tag && (
                  <span className="px-2 py-1 bg-yellow-500/15 text-yellow-600 rounded text-xs">{stock.popularity_tag}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 股票详情弹窗 */}
      {selectedStock && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-[#1E293B] rounded-lg p-6 max-w-lg w-full max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">{selectedStock.code} {selectedStock.name}</h3>
              <button onClick={() => setSelectedStock(null)} className="text-slate-400 hover:text-slate-200">✕</button>
            </div>
            <div className="mb-3">
              <span className={`text-2xl font-bold ${selectedStock.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                {selectedStock.change_pct > 0 ? '+' : ''}{selectedStock.change_pct?.toFixed(2)}%
              </span>
              <span className="ml-4 text-slate-400">热度: {(selectedStock.hot_score / 10000).toFixed(1)}万</span>
            </div>
            <div className="mb-3">
              <div className="font-bold text-sm mb-1">题材归因：</div>
              <div className="text-sm text-slate-300">{selectedStock.reason}</div>
            </div>
            {selectedStock.analyse && (
              <div className="mb-3">
                <div className="font-bold text-sm mb-1">详细分析：</div>
                <div className="text-sm text-slate-300 whitespace-pre-line">{selectedStock.analyse}</div>
              </div>
            )}
            <div className="flex flex-wrap gap-1">
              {selectedStock.concept_tags?.map((tag, j) => (
                <span key={j} className="px-2 py-1 bg-blue-500/15 text-blue-400 rounded text-xs">{tag}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 回测 */}
      <div className="bg-[#1E293B] rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">策略回测</h2>
          <button
            onClick={handleBacktest}
            className="bg-blue-500/100 text-white px-4 py-2 rounded hover:bg-blue-600 text-sm"
          >
            运行回测
          </button>
        </div>
        {backtest && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-xs text-slate-400">总收益</div>
              <div className="text-xl font-bold text-red-600">{backtest.total_return}%</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-400">胜率</div>
              <div className="text-xl font-bold">{backtest.win_rate}%</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-400">夏普比率</div>
              <div className="text-xl font-bold">{backtest.sharpe_ratio}</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-400">最大回撤</div>
              <div className="text-xl font-bold text-green-400">{backtest.max_drawdown}%</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-400">交易次数</div>
              <div className="text-xl font-bold">{backtest.total_trades}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
