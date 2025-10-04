"""
Unit tests for Polymarket Trading Agent
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from config import TradingConfig, APIConfig, MonitoringConfig, AgentConfig
from risk_manager import RiskManager, Trade, Position
from metrics import MetricsCollector


class TestTradingConfig(unittest.TestCase):
    """Test TradingConfig validation"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = TradingConfig()
        config.validate()  # Should not raise
    
    def test_invalid_min_liquidity(self):
        """Test invalid min_liquidity"""
        config = TradingConfig(min_liquidity=-100)
        with self.assertRaises(AssertionError):
            config.validate()
    
    def test_invalid_position_sizes(self):
        """Test invalid position sizes"""
        config = TradingConfig(
            min_position_size=100,
            max_position_size=50
        )
        with self.assertRaises(AssertionError):
            config.validate()
    
    def test_invalid_confidence_threshold(self):
        """Test invalid confidence threshold"""
        config = TradingConfig(confidence_threshold=1.5)
        with self.assertRaises(AssertionError):
            config.validate()
    
    def test_invalid_drawdown(self):
        """Test invalid drawdown percentage"""
        config = TradingConfig(max_drawdown_percent=1.5)
        with self.assertRaises(AssertionError):
            config.validate()


class TestRiskManager(unittest.TestCase):
    """Test RiskManager functionality"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.config = TradingConfig(
            max_position_size=100,
            min_position_size=10,
            max_daily_loss=500,
            max_weekly_loss=2000,
            max_drawdown_percent=0.20,
            max_total_positions=5,
            max_positions_per_market=1
        )
        self.risk_manager = RiskManager(self.config)
        self.risk_manager.set_initial_balance(10000)
    
    def test_initial_state(self):
        """Test initial risk manager state"""
        self.assertEqual(self.risk_manager.initial_balance, 10000)
        self.assertEqual(self.risk_manager.total_pnl, 0)
        self.assertEqual(len(self.risk_manager.positions), 0)
        self.assertFalse(self.risk_manager.is_halted)
    
    def test_can_trade_basic(self):
        """Test basic trade permission"""
        can_trade, reason = self.risk_manager.can_trade(50, "market_1")
        self.assertTrue(can_trade)
        self.assertEqual(reason, "OK")
    
    def test_position_size_limits(self):
        """Test position size limits"""
        # Too small
        can_trade, reason = self.risk_manager.can_trade(5, "market_1")
        self.assertFalse(can_trade)
        self.assertIn("too small", reason)
        
        # Too large
        can_trade, reason = self.risk_manager.can_trade(200, "market_1")
        self.assertFalse(can_trade)
        self.assertIn("too large", reason)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement"""
        # Simulate a large loss
        today = datetime.now().date().isoformat()
        self.risk_manager.daily_pnl[today] = -500
        
        can_trade, reason = self.risk_manager.can_trade(50, "market_1")
        self.assertFalse(can_trade)
        self.assertIn("Daily loss limit", reason)
        self.assertTrue(self.risk_manager.is_halted)
    
    def test_max_positions_limit(self):
        """Test maximum positions limit"""
        # Fill up positions
        for i in range(5):
            self.risk_manager.positions[f"market_{i}"] = Position(
                market_id=f"market_{i}",
                market_title=f"Market {i}",
                token_id=f"token_{i}",
                side="BUY",
                amount=50,
                entry_price=0.5,
                current_price=0.5
            )
        
        can_trade, reason = self.risk_manager.can_trade(50, "market_6")
        self.assertFalse(can_trade)
        self.assertIn("Max total positions", reason)
    
    def test_per_market_position_limit(self):
        """Test per-market position limit"""
        # Add a position in market_1
        self.risk_manager.positions["market_1"] = Position(
            market_id="market_1",
            market_title="Market 1",
            token_id="token_1",
            side="BUY",
            amount=50,
            entry_price=0.5,
            current_price=0.5
        )
        
        can_trade, reason = self.risk_manager.can_trade(50, "market_1")
        self.assertFalse(can_trade)
        self.assertIn("Max positions per market", reason)
    
    def test_record_trade(self):
        """Test trade recording"""
        trade = self.risk_manager.record_trade(
            market_id="market_1",
            market_title="Test Market",
            token_id="token_1",
            side="BUY",
            amount=50,
            price=0.5
        )
        
        self.assertEqual(len(self.risk_manager.trades), 1)
        self.assertEqual(len(self.risk_manager.positions), 1)
        self.assertIn("market_1", self.risk_manager.positions)
    
    def test_close_position_profit(self):
        """Test closing position with profit"""
        # Open position
        self.risk_manager.record_trade(
            market_id="market_1",
            market_title="Test Market",
            token_id="token_1",
            side="BUY",
            amount=100,
            price=0.5
        )
        
        # Close with profit
        pnl = self.risk_manager.close_position("market_1", exit_price=0.7)
        
        self.assertIsNotNone(pnl)
        self.assertGreater(pnl, 0)
        self.assertEqual(len(self.risk_manager.positions), 0)
        self.assertEqual(self.risk_manager.total_pnl, pnl)
        self.assertEqual(self.risk_manager.consecutive_losses, 0)
    
    def test_close_position_loss(self):
        """Test closing position with loss"""
        # Open position
        self.risk_manager.record_trade(
            market_id="market_1",
            market_title="Test Market",
            token_id="token_1",
            side="BUY",
            amount=100,
            price=0.5
        )
        
        # Close with loss
        pnl = self.risk_manager.close_position("market_1", exit_price=0.3)
        
        self.assertIsNotNone(pnl)
        self.assertLess(pnl, 0)
        self.assertEqual(self.risk_manager.consecutive_losses, 1)
    
    def test_kelly_position_sizing(self):
        """Test Kelly criterion position sizing"""
        self.config.use_kelly_criterion = True
        self.config.kelly_fraction = 0.25
        
        # Positive edge
        size = self.risk_manager.calculate_position_size(
            edge=0.15,
            price=0.5,
            confidence=0.8
        )
        
        self.assertGreater(size, 0)
        self.assertLessEqual(size, self.config.max_position_size)
        self.assertGreaterEqual(size, self.config.min_position_size)
    
    def test_portfolio_summary(self):
        """Test portfolio summary generation"""
        summary = self.risk_manager.get_portfolio_summary()
        
        self.assertIn("current_balance", summary)
        self.assertIn("total_pnl", summary)
        self.assertIn("daily_pnl", summary)
        self.assertIn("open_positions", summary)
        self.assertIn("drawdown", summary)
        
        self.assertEqual(summary["current_balance"], 10000)
        self.assertEqual(summary["open_positions"], 0)


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector functionality"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.metrics = MetricsCollector(metrics_file="test_metrics.json")
        self.config = TradingConfig()
        self.risk_manager = RiskManager(self.config)
        self.risk_manager.set_initial_balance(10000)
    
    def tearDown(self):
        """Cleanup test files"""
        import os
        if os.path.exists("test_metrics.json"):
            os.remove("test_metrics.json")
    
    def test_initial_state(self):
        """Test initial metrics state"""
        self.assertEqual(self.metrics.markets_scanned, 0)
        self.assertEqual(self.metrics.opportunities_found, 0)
        self.assertEqual(self.metrics.trades_executed, 0)
        self.assertEqual(self.metrics.api_calls, 0)
    
    def test_record_market_scan(self):
        """Test recording market scan"""
        self.metrics.record_market_scan(100, 5)
        
        self.assertEqual(self.metrics.markets_scanned, 100)
        self.assertEqual(self.metrics.opportunities_found, 5)
    
    def test_record_trade_execution(self):
        """Test recording trade execution"""
        self.metrics.record_trade_execution(success=True)
        self.metrics.record_trade_execution(success=False)
        
        self.assertEqual(self.metrics.trades_executed, 1)
        self.assertEqual(self.metrics.trades_failed, 1)
    
    def test_record_api_call(self):
        """Test recording API calls"""
        self.metrics.record_api_call(response_time=0.5, error=False)
        self.metrics.record_api_call(response_time=0, error=True)
        
        self.assertEqual(self.metrics.api_calls, 2)
        self.assertEqual(self.metrics.api_errors, 1)
        self.assertEqual(len(self.metrics.api_response_times), 1)
    
    def test_create_snapshot(self):
        """Test creating metrics snapshot"""
        # Add some activity
        self.metrics.record_market_scan(100, 10)
        self.metrics.record_trade_execution(success=True)
        
        snapshot = self.metrics.create_snapshot(
            self.risk_manager,
            self.risk_manager.trades
        )
        
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.markets_scanned, 100)
        self.assertEqual(snapshot.opportunities_found, 10)
        self.assertEqual(snapshot.trades_executed, 1)
    
    def test_performance_summary(self):
        """Test performance summary generation"""
        # Create a snapshot first
        self.metrics.create_snapshot(
            self.risk_manager,
            self.risk_manager.trades
        )
        
        summary = self.metrics.get_performance_summary()
        
        self.assertIn("latest_snapshot", summary)
        self.assertIn("total_snapshots", summary)
        self.assertIn("api_success_rate", summary)


class CircuitBreakerForTesting:
    """Circuit breaker implementation for testing (standalone)"""
    
    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.is_open:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed < self.timeout:
                    raise Exception(
                        f"Circuit breaker open. Retry in {self.timeout - elapsed:.0f}s"
                    )
                else:
                    self.is_open = False
                    self.failures = 0
        
        try:
            result = func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.threshold:
                self.is_open = True
            
            raise e


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker functionality"""
    
    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreakerForTesting(threshold=3, timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Trigger failures
        for i in range(3):
            with self.assertRaises(Exception):
                cb.call(failing_func)
        
        # Circuit should be open now
        self.assertTrue(cb.is_open)
        
        # Next call should fail immediately
        with self.assertRaises(Exception) as context:
            cb.call(failing_func)
        
        self.assertIn("Circuit breaker open", str(context.exception))
    
    def test_circuit_breaker_success_resets(self):
        """Test successful call resets failure count"""
        cb = CircuitBreakerForTesting(threshold=3, timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        def success_func():
            return "success"
        
        # Trigger some failures
        for i in range(2):
            with self.assertRaises(Exception):
                cb.call(failing_func)
        
        # Success should reset
        result = cb.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(cb.failures, 0)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
