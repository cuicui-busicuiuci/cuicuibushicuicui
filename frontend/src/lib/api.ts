// 动态获取API基础地址
// 生产部署：构建时设 NEXT_PUBLIC_API_URL='' 走 nginx 同源代理
// 开发环境：不设，自动推导 hostname:8017
function getApiBase() {
  const buildApiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (buildApiUrl !== undefined) {
    return buildApiUrl;
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname.includes('trycloudflare.com')) {
      return `https://${hostname}`;
    }
    return `http://${hostname}:8017`;
  }
  return 'http://localhost:8017';
}

const API_BASE = getApiBase();

export async function fetchApi(endpoint: string) {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function postApi(endpoint: string) {
  const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function scanApi(endpoint: string) {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function getHealth() { return fetchApi('/api/system/health'); }
export async function getQuote(code: string) { return fetchApi(`/api/market/quote/${code}`); }
export async function getHotStocks() { return fetchApi('/api/signal/hot'); }
export async function getSentiment() { return fetchApi('/api/strategy/sentiment'); }
export async function getLeaderSignals() { return fetchApi('/api/strategy/leader'); }
export async function getFirstBoardSignals() { return fetchApi('/api/strategy/first-board'); }
export async function getSecondBoardSignals() { return fetchApi('/api/strategy/signals?strategy=second_board'); }
export async function getLeaderDipSignals() { return fetchApi('/api/strategy/signals?strategy=leader_dip'); }
export async function getMainWaveSignals() { return fetchApi('/api/strategy/signals?strategy=main_wave'); }
export async function getWeakToStrongSignals() { return fetchApi('/api/strategy/signals?strategy=weak_to_strong'); }
export async function getMoneyFlowSignals() { return fetchApi('/api/strategy/signals?strategy=money_flow'); }
export async function getRecommendations() { return fetchApi('/api/recommendation/today'); }
export async function getMarketRisk() { return fetchApi('/api/risk/market'); }
export async function runBacktest(strategy?: string) {
  const url = strategy ? `/api/backtest/run?strategy=${strategy}` : '/api/backtest/run';
  return postApi(url);
}
export async function getFactorRank() { return fetchApi('/api/factor/rank?top=10'); }
export async function getAiScore() { return fetchApi('/api/factor/ai-score?top=10'); }
export async function getLeaders() { return fetchApi('/api/models/leaders'); }
export async function getMoneyFlow() { return fetchApi('/api/models/money-flow'); }
export async function runFullScan(maxStocks = 0, minScore = 50) {
  return scanApi(`/api/scan/full?max_stocks=${maxStocks}&min_score=${minScore}`);
}
export async function getScanProgress() { return scanApi('/api/scan/full?max_stocks=0&min_score=40'); }

// 模拟交易
export async function getTradeStatus() { return fetchApi('/api/trade/status'); }
export async function runTrade() { return postApi('/api/trade/run'); }
export async function generateReport() { return postApi('/api/trade/report'); }
export async function getTradeReport(date?: string) {
  return fetchApi(`/api/trade/report${date ? `?date_str=${date}` : ''}`);
}
export async function getTradeReports(limit = 10) { return fetchApi(`/api/trade/reports?limit=${limit}`); }
export async function getTradeDashboard() { return fetchApi('/api/trade/dashboard'); }
export async function startAutoTrader() { return postApi('/api/trade/auto/start'); }
export async function stopAutoTrader() { return postApi('/api/trade/auto/stop'); }
export async function getAutoTraderStatus() { return fetchApi('/api/trade/auto/status'); }

// 策略优化
export async function runOptimization() { return postApi('/api/optimizer/run'); }
export async function getOptimizationReport() { return fetchApi('/api/optimizer/report'); }
export async function startAutoOptimizer() { return postApi('/api/optimizer/auto/start'); }
export async function stopAutoOptimizer() { return postApi('/api/optimizer/auto/stop'); }
export async function getAutoOptimizerStatus() { return fetchApi('/api/optimizer/auto/status'); }
export async function getBestParams() { return fetchApi('/api/optimizer/best'); }

// SSE 实时流
export function createTradeStreamUrl(): string {
  return `${API_BASE}/api/trade/stream`;
}
