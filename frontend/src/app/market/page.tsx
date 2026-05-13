'use client';

import { useEffect, useState } from 'react';
import { getHotStocks, getQuote } from '@/lib/api';
import Link from 'next/link';

interface HotStock {
  code: string;
  name: string;
  reason: string;
  change_pct: number;
  hot_score: number;
  concept_tags: string[];
  popularity_tag: string;
}

interface Quote {
  code: string;
  name: string;
  price: number;
  open: number;
  high: number;
  low: number;
  last_close: number;
  change_amt: number;
  change_pct: number;
  turnover_pct: number;
  pe_ttm: number;
  pb: number;
  mcap_yi: number;
  limit_up: number;
  limit_down: number;
  amount_wan: number;
  vol_ratio: number;
}

export default function MarketPage() {
  const [hotStocks, setHotStocks] = useState<HotStock[]>([]);
  const [selectedStock, setSelectedStock] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    loadData();
    // 30秒自动刷新
    const timer = setInterval(loadData, 30000);
    return () => clearInterval(timer);
  }, []);

  async function loadData() {
    try {
      const hotRes = await getHotStocks();
      setHotStocks(hotRes.data || []);
    } catch (error) {
      console.error('加载失败:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleStockClick(code: string) {
    try {
      const quoteRes = await getQuote(code);
      setSelectedStock(quoteRes.data);
    } catch (error) {
      console.error('获取行情失败:', error);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] p-2 md:p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-blue-400 text-sm">← 返回</Link>
          <h1 className="text-lg md:text-2xl font-bold">实时行情</h1>
        </div>
        {lastUpdate && (
          <span className="text-xs text-slate-500">更新 {lastUpdate}</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* 热点股票列表 */}
        <div className="lg:col-span-2 bg-[#1E293B] rounded-lg shadow overflow-hidden">
          <div className="p-3 border-b flex justify-between items-center">
            <h2 className="font-bold">今日热点 ({hotStocks.length}只)</h2>
            <span className="text-xs text-slate-500">点击查看详情</span>
          </div>
          <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
            <table className="w-full text-xs md:text-sm">
              <thead>
                <tr className="bg-[#020617] border-b">
                  <th className="text-left py-2 px-2">代码</th>
                  <th className="text-left py-2 px-2">名称</th>
                  <th className="text-right py-2 px-2">涨幅</th>
                  <th className="text-right py-2 px-2 hidden md:table-cell">热度</th>
                  <th className="text-left py-2 px-2 hidden md:table-cell">题材</th>
                  <th className="text-left py-2 px-2">标签</th>
                </tr>
              </thead>
              <tbody>
                {hotStocks.map((stock, i) => (
                  <tr key={i} className="border-b hover:bg-blue-500/100/10 cursor-pointer active:bg-blue-500/15"
                    onClick={() => handleStockClick(stock.code)}>
                    <td className="py-1.5 px-2 font-mono">{stock.code}</td>
                    <td className="py-1.5 px-2 font-bold">{stock.name}</td>
                    <td className={`py-1.5 px-2 text-right font-bold ${stock.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                      {stock.change_pct > 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                    </td>
                    <td className="py-1.5 px-2 text-right text-xs hidden md:table-cell">
                      {(stock.hot_score / 10000).toFixed(0)}万
                    </td>
                    <td className="py-1.5 px-2 hidden md:table-cell">
                      <div className="flex flex-wrap gap-0.5 max-w-[200px]">
                        {stock.concept_tags?.slice(0, 2).map((tag, j) => (
                          <span key={j} className="px-1 py-0.5 bg-blue-500/15 text-blue-400 rounded text-xs">{tag}</span>
                        ))}
                      </div>
                    </td>
                    <td className="py-1.5 px-2">
                      <span className="px-1.5 py-0.5 bg-yellow-500/15 text-yellow-300 rounded text-xs whitespace-nowrap">
                        {stock.popularity_tag || '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 个股详情 */}
        <div className="bg-[#1E293B] rounded-lg shadow p-3">
          <h2 className="font-bold mb-3">个股详情</h2>
          {selectedStock ? (
            <div className="space-y-3">
              <div className="text-center">
                <div className="text-xl font-bold">{selectedStock.name}</div>
                <div className="text-slate-500 text-sm">{selectedStock.code}</div>
              </div>

              <div className="text-center">
                <div className={`text-3xl font-bold ${selectedStock.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                  {selectedStock.price?.toFixed(2)}
                </div>
                <div className={`text-base ${selectedStock.change_pct > 0 ? 'text-red-600' : 'text-green-400'}`}>
                  {selectedStock.change_pct > 0 ? '+' : ''}{selectedStock.change_pct?.toFixed(2)}%
                  <span className="text-slate-500 text-sm ml-1">
                    {selectedStock.change_amt > 0 ? '+' : ''}{selectedStock.change_amt?.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* 价格区间 */}
              <div className="bg-[#020617] rounded p-2 text-xs">
                <div className="flex justify-between">
                  <span>开盘 {selectedStock.open?.toFixed(2)}</span>
                  <span>昨收 {selectedStock.last_close?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-red-400">最高 {selectedStock.high?.toFixed(2)}</span>
                  <span className="text-green-400">最低 {selectedStock.low?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span>涨停 {selectedStock.limit_up?.toFixed(2)}</span>
                  <span>跌停 {selectedStock.limit_down?.toFixed(2)}</span>
                </div>
              </div>

              {/* 技术指标 */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">PE(TTM)</div>
                  <div className="font-bold">{selectedStock.pe_ttm > 0 ? selectedStock.pe_ttm?.toFixed(1) : '亏损'}</div>
                </div>
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">PB</div>
                  <div className="font-bold">{selectedStock.pb?.toFixed(2)}</div>
                </div>
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">总市值</div>
                  <div className="font-bold">{selectedStock.mcap_yi > 10000 ? (selectedStock.mcap_yi/10000).toFixed(0)+'万' : selectedStock.mcap_yi?.toFixed(0)}{selectedStock.mcap_yi > 10000 ? '亿' : '亿'}</div>
                </div>
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">换手率</div>
                  <div className="font-bold">{selectedStock.turnover_pct?.toFixed(2)}%</div>
                </div>
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">成交额</div>
                  <div className="font-bold">{selectedStock.amount_wan > 10000 ? (selectedStock.amount_wan/10000).toFixed(1)+'亿' : (selectedStock.amount_wan||0).toFixed(0)+'万'}</div>
                </div>
                <div className="bg-[#020617] rounded p-2">
                  <div className="text-slate-500">量比</div>
                  <div className="font-bold">{selectedStock.vol_ratio?.toFixed(2)}</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-slate-500 py-8 text-sm">
              点击左侧股票<br/>查看实时行情和指标
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
