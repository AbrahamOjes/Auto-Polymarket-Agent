"""
Metrics collection and monitoring for Polymarket Trading Agent
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time"""
    timestamp: str
    
    # Performance metrics
    total_pnl: float
    daily_pnl: float
    weekly_pnl: float
    win_rate: float
    sharpe_ratio: Optional[float]
    
    # Portfolio metrics
    current_balance: float
    drawdown: float
    open_positions: int
    total_trades: int
    
    # Risk metrics
    max_drawdown: float
    consecutive_losses: int
    is_halted: bool
    
    # Market metrics
    markets_scanned: int
    opportunities_found: int
    trades_executed: int
    trades_failed: int
    
    # API metrics
    api_calls: int
    api_errors: int
    avg_response_time: float


class MetricsCollector:
    """Collects and persists trading metrics"""
    
    def __init__(self, metrics_file: str = "metrics.json"):
        """
        Initialize metrics collector
        
        Args:
            metrics_file: Path to metrics file
        """
        self.metrics_file = Path(metrics_file)
        self.snapshots: List[MetricSnapshot] = []
        
        # Runtime counters
        self.markets_scanned = 0
        self.opportunities_found = 0
        self.trades_executed = 0
        self.trades_failed = 0
        self.api_calls = 0
        self.api_errors = 0
        self.api_response_times: List[float] = []
        
        # Load existing metrics
        self._load_metrics()
        
        logger.info(f"Metrics collector initialized (file: {metrics_file})")
    
    def record_market_scan(self, num_markets: int, num_opportunities: int) -> None:
        """Record a market scan cycle"""
        self.markets_scanned += num_markets
        self.opportunities_found += num_opportunities
        logger.debug(
            f"Market scan recorded: {num_markets} markets, "
            f"{num_opportunities} opportunities"
        )
    
    def record_trade_execution(self, success: bool) -> None:
        """Record a trade execution attempt"""
        if success:
            self.trades_executed += 1
        else:
            self.trades_failed += 1
        logger.debug(f"Trade execution recorded: {'success' if success else 'failed'}")
    
    def record_api_call(self, response_time: float, error: bool = False) -> None:
        """Record an API call"""
        self.api_calls += 1
        if error:
            self.api_errors += 1
        else:
            self.api_response_times.append(response_time)
        
        # Keep only last 1000 response times
        if len(self.api_response_times) > 1000:
            self.api_response_times = self.api_response_times[-1000:]
    
    def create_snapshot(
        self,
        risk_manager,
        trades: List
    ) -> MetricSnapshot:
        """
        Create a metrics snapshot
        
        Args:
            risk_manager: RiskManager instance
            trades: List of Trade objects
        
        Returns:
            MetricSnapshot
        """
        portfolio = risk_manager.get_portfolio_summary()
        
        # Calculate win rate
        closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]
        win_rate = 0.0
        if closed_trades:
            winning_trades = sum(1 for t in closed_trades if t.pnl > 0)
            win_rate = winning_trades / len(closed_trades)
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = None
        if closed_trades and len(closed_trades) >= 2:
            returns = [t.pnl for t in closed_trades]
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            if std_dev > 0:
                sharpe_ratio = avg_return / std_dev
        
        # Average API response time
        avg_response_time = 0.0
        if self.api_response_times:
            avg_response_time = sum(self.api_response_times) / len(self.api_response_times)
        
        snapshot = MetricSnapshot(
            timestamp=datetime.now().isoformat(),
            total_pnl=portfolio["total_pnl"],
            daily_pnl=portfolio["daily_pnl"],
            weekly_pnl=portfolio["weekly_pnl"],
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            current_balance=portfolio["current_balance"],
            drawdown=portfolio["drawdown"],
            open_positions=portfolio["open_positions"],
            total_trades=portfolio["total_trades"],
            max_drawdown=risk_manager.config.max_drawdown_percent,
            consecutive_losses=portfolio["consecutive_losses"],
            is_halted=portfolio["is_halted"],
            markets_scanned=self.markets_scanned,
            opportunities_found=self.opportunities_found,
            trades_executed=self.trades_executed,
            trades_failed=self.trades_failed,
            api_calls=self.api_calls,
            api_errors=self.api_errors,
            avg_response_time=avg_response_time
        )
        
        self.snapshots.append(snapshot)
        self._save_metrics()
        
        logger.info(
            f"Metrics snapshot created: PnL=${snapshot.total_pnl:.2f}, "
            f"Win Rate={snapshot.win_rate:.2%}, "
            f"Positions={snapshot.open_positions}"
        )
        
        return snapshot
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary from all snapshots"""
        if not self.snapshots:
            return {}
        
        latest = self.snapshots[-1]
        
        # Calculate metrics over time
        pnl_history = [s.total_pnl for s in self.snapshots]
        max_pnl = max(pnl_history) if pnl_history else 0
        min_pnl = min(pnl_history) if pnl_history else 0
        
        return {
            "latest_snapshot": asdict(latest),
            "total_snapshots": len(self.snapshots),
            "max_pnl": max_pnl,
            "min_pnl": min_pnl,
            "pnl_range": max_pnl - min_pnl,
            "api_success_rate": (
                (self.api_calls - self.api_errors) / self.api_calls
                if self.api_calls > 0 else 0
            ),
            "trade_success_rate": (
                self.trades_executed / (self.trades_executed + self.trades_failed)
                if (self.trades_executed + self.trades_failed) > 0 else 0
            )
        }
    
    def print_summary(self) -> None:
        """Print formatted metrics summary"""
        summary = self.get_performance_summary()
        
        if not summary:
            print("No metrics available yet")
            return
        
        latest = summary["latest_snapshot"]
        
        print("\n" + "="*60)
        print("POLYMARKET TRADING AGENT - PERFORMANCE SUMMARY")
        print("="*60)
        
        print("\n📊 PORTFOLIO METRICS")
        print(f"  Current Balance:    ${latest['current_balance']:,.2f}")
        print(f"  Total P&L:          ${latest['total_pnl']:+,.2f}")
        print(f"  Daily P&L:          ${latest['daily_pnl']:+,.2f}")
        print(f"  Weekly P&L:         ${latest['weekly_pnl']:+,.2f}")
        print(f"  Drawdown:           {latest['drawdown']:.2%}")
        
        print("\n📈 TRADING METRICS")
        print(f"  Total Trades:       {latest['total_trades']}")
        print(f"  Open Positions:     {latest['open_positions']}")
        print(f"  Win Rate:           {latest['win_rate']:.2%}")
        if latest['sharpe_ratio'] is not None:
            print(f"  Sharpe Ratio:       {latest['sharpe_ratio']:.3f}")
        print(f"  Consecutive Losses: {latest['consecutive_losses']}")
        
        print("\n🔍 MARKET SCANNING")
        print(f"  Markets Scanned:    {latest['markets_scanned']}")
        print(f"  Opportunities:      {latest['opportunities_found']}")
        print(f"  Trades Executed:    {latest['trades_executed']}")
        print(f"  Trades Failed:      {latest['trades_failed']}")
        
        print("\n🌐 API METRICS")
        print(f"  API Calls:          {latest['api_calls']}")
        print(f"  API Errors:         {latest['api_errors']}")
        print(f"  Success Rate:       {summary['api_success_rate']:.2%}")
        print(f"  Avg Response Time:  {latest['avg_response_time']:.3f}s")
        
        print("\n⚠️  STATUS")
        status = "🔴 HALTED" if latest['is_halted'] else "🟢 ACTIVE"
        print(f"  Trading Status:     {status}")
        
        print("\n" + "="*60 + "\n")
    
    def _save_metrics(self) -> None:
        """Save metrics to file"""
        try:
            data = {
                "snapshots": [asdict(s) for s in self.snapshots],
                "counters": {
                    "markets_scanned": self.markets_scanned,
                    "opportunities_found": self.opportunities_found,
                    "trades_executed": self.trades_executed,
                    "trades_failed": self.trades_failed,
                    "api_calls": self.api_calls,
                    "api_errors": self.api_errors
                }
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Metrics saved to {self.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _load_metrics(self) -> None:
        """Load metrics from file"""
        if not self.metrics_file.exists():
            logger.info("No existing metrics file found")
            return
        
        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
            
            # Load snapshots
            self.snapshots = [
                MetricSnapshot(**s) for s in data.get("snapshots", [])
            ]
            
            # Load counters
            counters = data.get("counters", {})
            self.markets_scanned = counters.get("markets_scanned", 0)
            self.opportunities_found = counters.get("opportunities_found", 0)
            self.trades_executed = counters.get("trades_executed", 0)
            self.trades_failed = counters.get("trades_failed", 0)
            self.api_calls = counters.get("api_calls", 0)
            self.api_errors = counters.get("api_errors", 0)
            
            logger.info(f"Loaded {len(self.snapshots)} metric snapshots")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
