'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { getSentiment, getLeaderSignals, getFirstBoardSignals, getSecondBoardSignals, getLeaderDipSignals, getMainWaveSignals, getWeakToStrongSignals, getMoneyFlowSignals, getRecommendations } from '@/lib/api';

interface MarketSnapshot {
  type: string;
  timestamp: string;
  sentiment: any;
  strategies: Record<string, any[]>;
  recommendations: any[];
  hot_stocks: any[];
  total_signals: number;
}

export function useMarketData() {
  const [data, setData] = useState<MarketSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState('');
  const timerRef = useRef<any>(null);

  const fetchData = useCallback(async () => {
    try {
      const results = await Promise.all([
        getSentiment(), getLeaderSignals(), getFirstBoardSignals(), getSecondBoardSignals(),
        getLeaderDipSignals(), getMainWaveSignals(), getWeakToStrongSignals(), getMoneyFlowSignals(),
        getRecommendations(),
      ]);

      const [sentimentRes, leaderRes, firstBoardRes, secondBoardRes, leaderDipRes, mainWaveRes, weakRes, moneyRes, recRes] = results;

      const strategies: Record<string, any[]> = {
        leader: leaderRes.data || [],
        first_board: firstBoardRes.data || [],
        second_board: secondBoardRes.data || [],
        leader_dip: leaderDipRes.data || [],
        main_wave: mainWaveRes.data || [],
        weak_to_strong: weakRes.data || [],
        money_flow: moneyRes.data || [],
      };

      const totalSignals = Object.values(strategies).reduce((sum, arr) => sum + arr.length, 0);

      setData({
        type: 'market_snapshot',
        timestamp: new Date().toISOString(),
        sentiment: sentimentRes.data,
        strategies,
        recommendations: recRes.data?.recommendations || [],
        hot_stocks: [],
        total_signals: totalSignals,
      });
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
      setError(null);
    } catch (e: any) {
      console.error('data load fail:', e.message || e);
      setError(e.message || 'request failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, 10000);
    return () => clearInterval(timerRef.current);
  }, [fetchData]);

  return { data, loading, error, lastUpdate, refresh: fetchData };
}
