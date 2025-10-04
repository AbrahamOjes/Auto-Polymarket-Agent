"""
Enhanced Autonomous Polymarket Trading Agent
Includes risk management, metrics, error handling, and paper trading
"""

import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

from config import load_config, AgentConfig
from risk_manager import RiskManager, Trade
from metrics import MetricsCollector


def setup_logging(config) -> logging.Logger:
    """Setup logging with file rotation"""
    logger = logging.getLogger("polymarket_agent")
    logger.setLevel(getattr(logging, config.monitoring.log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.monitoring.log_file:
        file_handler = RotatingFileHandler(
            config.monitoring.log_file,
            maxBytes=config.monitoring.log_max_bytes,
            backupCount=config.monitoring.log_backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class CircuitBreaker:
    """Circuit breaker for API calls"""
    
    def __init__(self, threshold: int, timeout: int):
        """
        Initialize circuit breaker
        
        Args:
            threshold: Number of failures before opening
            timeout: Seconds to wait before trying again
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        # Check if circuit is open
        if self.is_open:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed < self.timeout:
                    raise Exception(
                        f"Circuit breaker open. Retry in {self.timeout - elapsed:.0f}s"
                    )
                else:
                    # Try to close circuit
                    self.is_open = False
                    self.failures = 0
        
        try:
            result = func(*args, **kwargs)
            # Success - reset failures
            self.failures = 0
            return result
        except Exception as e:
            # Failure - increment counter
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.threshold:
                self.is_open = True
            
            raise e
    
    def reset(self):
        """Reset circuit breaker"""
        self.failures = 0
        self.is_open = False
        self.last_failure_time = None


class EnhancedPolymarketAgent:
    """Enhanced autonomous agent with risk management and monitoring"""
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the enhanced Polymarket trading agent
        
        Args:
            config: AgentConfig instance
        """
        self.config = config
        self.logger = setup_logging(config)
        
        # Initialize components
        self.risk_manager = RiskManager(config.trading)
        self.metrics = MetricsCollector(config.monitoring.metrics_file)
        
        # Circuit breakers
        self.api_circuit_breaker = CircuitBreaker(
            threshold=config.api.circuit_breaker_threshold,
            timeout=config.api.circuit_breaker_timeout
        )
        
        # Setup HTTP session with retries
        self.session = self._create_session()
        
        # Initialize CLOB client (only if not paper trading)
        self.clob_client = None
        if not config.paper_trading:
            try:
                self.clob_client = ClobClient(
                    host=config.api.clob_host,
                    key=config.private_key,
                    chain_id=config.api.chain_id,
                    signature_type=config.api.signature_type
                )
                self.clob_client.set_api_creds(
                    self.clob_client.create_or_derive_api_creds()
                )
                self.logger.info("CLOB client initialized for LIVE trading")
            except Exception as e:
                self.logger.error(f"Failed to initialize CLOB client: {e}")
                raise
        else:
            self.logger.warning("Running in PAPER TRADING mode - no real trades will be executed")
        
        # Set initial balance (you should get this from wallet in production)
        initial_balance = 10000.0  # Default for paper trading
        if not config.paper_trading and self.clob_client:
            try:
                # Get actual balance from wallet
                # balance = self.clob_client.get_balance()  # Implement this
                pass
            except Exception as e:
                self.logger.warning(f"Could not fetch wallet balance: {e}")
        
        self.risk_manager.set_initial_balance(initial_balance)
        
        self.logger.info(
            f"Enhanced Polymarket Agent initialized\n"
            f"  Mode: {'PAPER TRADING' if config.paper_trading else 'LIVE TRADING'}\n"
            f"  Initial Balance: ${initial_balance:,.2f}\n"
            f"  Max Position Size: ${config.trading.max_position_size}\n"
            f"  Confidence Threshold: {config.trading.confidence_threshold:.2%}"
        )
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.api.max_retries,
            backoff_factor=self.config.api.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_markets(self, limit: int = None) -> List[Dict]:
        """Fetch active markets with error handling"""
        if limit is None:
            limit = self.config.api.markets_fetch_limit
        
        try:
            start_time = time.time()
            
            def _fetch():
                response = self.session.get(
                    f"{self.config.api.gamma_api}/markets",
                    params={"limit": limit, "active": True},
                    timeout=self.config.api.request_timeout
                )
                response.raise_for_status()
                return response.json()
            
            markets = self.api_circuit_breaker.call(_fetch)
            
            response_time = time.time() - start_time
            self.metrics.record_api_call(response_time)
            
            self.logger.info(f"Fetched {len(markets)} active markets")
            return markets
            
        except requests.exceptions.Timeout:
            self.logger.error("Market fetch timeout")
            self.metrics.record_api_call(0, error=True)
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Market fetch failed: {e}")
            self.metrics.record_api_call(0, error=True)
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching markets: {e}")
            self.metrics.record_api_call(0, error=True)
            return []
    
    def get_market_details(self, condition_id: str) -> Optional[Dict]:
        """Get detailed market information with error handling"""
        try:
            start_time = time.time()
            
            def _fetch():
                response = self.session.get(
                    f"{self.config.api.gamma_api}/markets/{condition_id}",
                    timeout=self.config.api.request_timeout
                )
                response.raise_for_status()
                return response.json()
            
            market = self.api_circuit_breaker.call(_fetch)
            
            response_time = time.time() - start_time
            self.metrics.record_api_call(response_time)
            
            return market
            
        except Exception as e:
            self.logger.error(f"Error fetching market {condition_id}: {e}")
            self.metrics.record_api_call(0, error=True)
            return None
    
    def analyze_market(self, market: Dict) -> Dict:
        """Analyze market for trading opportunities"""
        analysis = {
            "market_id": market.get("condition_id"),
            "title": market.get("question"),
            "opportunity": False,
            "side": None,
            "confidence": 0.0,
            "expected_value": 0.0,
            "recommended_size": 0.0
        }
        
        try:
            # Skip if insufficient liquidity
            liquidity = market.get("liquidity", 0)
            if liquidity < self.config.trading.min_liquidity:
                return analysis
            
            # Get current market prices
            tokens = market.get("tokens", [])
            if len(tokens) < 2:
                return analysis
            
            yes_price = float(tokens[0].get("price", 0))
            no_price = float(tokens[1].get("price", 0))
            
            # Validate prices
            if yes_price <= 0 or yes_price >= 1 or no_price <= 0 or no_price >= 1:
                self.logger.warning(f"Invalid prices for market {market.get('question')}")
                return analysis
            
            # Calculate expected probabilities
            estimated_yes_prob = self._estimate_probability(market)
            
            # Calculate edge
            market_yes_prob = yes_price
            edge = estimated_yes_prob - market_yes_prob
            
            # Determine if there's an opportunity
            if abs(edge) > self.config.trading.confidence_threshold:
                confidence = min(abs(edge) * 2, 1.0)  # Scale confidence
                
                # Calculate position size using Kelly criterion
                recommended_size = self.risk_manager.calculate_position_size(
                    edge=edge,
                    price=yes_price,
                    confidence=confidence
                )
                
                analysis["opportunity"] = True
                analysis["side"] = BUY if edge > 0 else SELL
                analysis["confidence"] = confidence
                analysis["recommended_size"] = recommended_size
                analysis["expected_value"] = self._calculate_ev(
                    edge, yes_price, no_price, recommended_size
                )
                
                self.logger.info(
                    f"Opportunity: {market.get('question')[:60]}...\n"
                    f"  Edge: {edge:+.2%} | Confidence: {confidence:.2%} | "
                    f"Size: ${recommended_size:.2f} | EV: ${analysis['expected_value']:.2f}"
                )
        
        except Exception as e:
            self.logger.error(f"Error analyzing market: {e}")
        
        return analysis
    
    def _estimate_probability(self, market: Dict) -> float:
        """
        Estimate true probability of event
        
        PLACEHOLDER: Implement your prediction model here
        - News sentiment analysis
        - Historical data analysis
        - Expert forecasts aggregation
        - Statistical models
        - LLM-based reasoning
        
        Currently returns market price (no edge)
        """
        tokens = market.get("tokens", [])
        if tokens:
            return float(tokens[0].get("price", 0.5))
        return 0.5
    
    def _calculate_ev(
        self,
        edge: float,
        yes_price: float,
        no_price: float,
        position_size: float
    ) -> float:
        """Calculate expected value of trade"""
        if edge > 0:  # Buying YES
            win_amount = (1 - yes_price) * position_size
            loss_amount = yes_price * position_size
            prob_win = yes_price + edge
        else:  # Buying NO
            win_amount = yes_price * position_size
            loss_amount = (1 - yes_price) * position_size
            prob_win = 1 - (yes_price + edge)
        
        ev = (prob_win * win_amount) - ((1 - prob_win) * loss_amount)
        return ev
    
    def execute_trade(
        self,
        market_id: str,
        market_title: str,
        token_id: str,
        side: str,
        amount: float,
        price: float
    ) -> bool:
        """
        Execute a trade (real or paper)
        
        Returns:
            True if successful, False otherwise
        """
        # Check risk limits
        can_trade, reason = self.risk_manager.can_trade(amount, market_id)
        if not can_trade:
            self.logger.warning(f"Trade blocked: {reason}")
            return False
        
        if self.config.paper_trading:
            # Paper trading - simulate execution
            self.logger.info(
                f"[PAPER TRADE] {side} ${amount:.2f} in {market_title[:50]}... @ {price:.3f}"
            )
            
            # Record the trade
            self.risk_manager.record_trade(
                market_id=market_id,
                market_title=market_title,
                token_id=token_id,
                side=side,
                amount=amount,
                price=price,
                status="open"
            )
            
            self.metrics.record_trade_execution(success=True)
            return True
        
        else:
            # Live trading - execute real order
            try:
                order = MarketOrderArgs(
                    token_id=token_id,
                    amount=amount,
                    side=side,
                    order_type=OrderType.FOK
                )
                
                signed_order = self.clob_client.create_market_order(order)
                response = self.clob_client.post_order(signed_order, OrderType.FOK)
                
                self.logger.info(f"[LIVE TRADE] Executed: {response}")
                
                # Record the trade
                self.risk_manager.record_trade(
                    market_id=market_id,
                    market_title=market_title,
                    token_id=token_id,
                    side=side,
                    amount=amount,
                    price=price,
                    status="open"
                )
                
                self.metrics.record_trade_execution(success=True)
                return True
                
            except Exception as e:
                self.logger.error(f"Trade execution failed: {e}")
                self.metrics.record_trade_execution(success=False)
                return False
    
    def run_cycle(self) -> None:
        """Run one cycle of market scanning and trading"""
        self.logger.info("="*60)
        self.logger.info("Starting market scan cycle...")
        
        try:
            # Fetch active markets
            markets = self.get_markets()
            
            if not markets:
                self.logger.warning("No markets fetched, skipping cycle")
                return
            
            # Analyze each market
            opportunities = []
            for market in markets:
                try:
                    analysis = self.analyze_market(market)
                    if analysis["opportunity"]:
                        opportunities.append(analysis)
                except Exception as e:
                    self.logger.error(f"Error analyzing market: {e}")
                    continue
            
            # Record scan metrics
            self.metrics.record_market_scan(len(markets), len(opportunities))
            
            self.logger.info(
                f"Scan complete: {len(markets)} markets, "
                f"{len(opportunities)} opportunities found"
            )
            
            if not opportunities:
                self.logger.info("No trading opportunities found")
                return
            
            # Sort by expected value
            opportunities.sort(key=lambda x: x["expected_value"], reverse=True)
            
            # Execute top opportunities
            trades_attempted = 0
            trades_executed = 0
            
            for opp in opportunities[:self.config.trading.top_opportunities_to_trade]:
                trades_attempted += 1
                
                self.logger.info(
                    f"\nAttempting trade {trades_attempted}: {opp['title'][:60]}..."
                )
                
                # Get market details
                market = self.get_market_details(opp["market_id"])
                if not market:
                    self.logger.warning("Could not fetch market details, skipping")
                    continue
                
                tokens = market.get("tokens", [])
                if not tokens:
                    self.logger.warning("No tokens found in market, skipping")
                    continue
                
                token_id = tokens[0]["token_id"]
                price = float(tokens[0].get("price", 0))
                
                # Execute trade
                success = self.execute_trade(
                    market_id=opp["market_id"],
                    market_title=opp["title"],
                    token_id=token_id,
                    side=opp["side"],
                    amount=opp["recommended_size"],
                    price=price
                )
                
                if success:
                    trades_executed += 1
                
                # Rate limiting
                time.sleep(self.config.trading.rate_limit_delay)
            
            self.logger.info(
                f"\nCycle complete: {trades_executed}/{trades_attempted} trades executed"
            )
            
            # Create metrics snapshot
            snapshot = self.metrics.create_snapshot(
                self.risk_manager,
                self.risk_manager.trades
            )
            
            # Print portfolio summary
            portfolio = self.risk_manager.get_portfolio_summary()
            self.logger.info(
                f"\nPortfolio Status:\n"
                f"  Balance: ${portfolio['current_balance']:,.2f}\n"
                f"  Total P&L: ${portfolio['total_pnl']:+,.2f}\n"
                f"  Daily P&L: ${portfolio['daily_pnl']:+,.2f}\n"
                f"  Open Positions: {portfolio['open_positions']}\n"
                f"  Drawdown: {portfolio['drawdown']:.2%}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in run cycle: {e}", exc_info=True)
    
    def run_continuous(self) -> None:
        """Run agent continuously"""
        self.logger.info("\n" + "="*60)
        self.logger.info("STARTING AUTONOMOUS TRADING AGENT")
        self.logger.info("="*60)
        self.logger.info(f"Mode: {'PAPER TRADING' if self.config.paper_trading else 'LIVE TRADING'}")
        self.logger.info(f"Scan Interval: {self.config.scan_interval_seconds}s")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("="*60 + "\n")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"CYCLE #{cycle_count}")
                self.logger.info(f"{'='*60}")
                
                self.run_cycle()
                
                # Print metrics summary every 10 cycles
                if cycle_count % 10 == 0:
                    self.metrics.print_summary()
                
                self.logger.info(
                    f"\nSleeping for {self.config.scan_interval_seconds} seconds..."
                )
                time.sleep(self.config.scan_interval_seconds)
                
            except KeyboardInterrupt:
                self.logger.info("\n\nAgent stopped by user")
                self.metrics.print_summary()
                break
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                self.logger.info("Waiting 60 seconds before retry...")
                time.sleep(60)


def main():
    """Main entry point"""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize and run agent
        agent = EnhancedPolymarketAgent(config)
        agent.run_continuous()
        
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
