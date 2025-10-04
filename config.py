"""
Configuration management for Polymarket Trading Agent
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TradingConfig:
    """Trading strategy configuration"""
    
    # Liquidity filters
    min_liquidity: float = 10000.0
    max_liquidity: Optional[float] = None
    
    # Position sizing
    max_position_size: float = 100.0
    min_position_size: float = 10.0
    
    # Risk management
    confidence_threshold: float = 0.10  # 10% edge required
    max_daily_loss: float = 500.0
    max_weekly_loss: float = 2000.0
    max_drawdown_percent: float = 0.20  # 20% max drawdown
    
    # Position limits
    max_positions_per_market: int = 1
    max_total_positions: int = 10
    max_position_concentration: float = 0.30  # Max 30% in single market
    
    # Execution
    top_opportunities_to_trade: int = 5
    rate_limit_delay: float = 2.0  # Seconds between trades
    
    # Kelly criterion for position sizing
    use_kelly_criterion: bool = True
    kelly_fraction: float = 0.25  # Use 25% of Kelly
    
    def validate(self) -> None:
        """Validate configuration parameters"""
        assert self.min_liquidity > 0, "min_liquidity must be positive"
        assert self.max_position_size > self.min_position_size, \
            "max_position_size must be greater than min_position_size"
        assert 0 < self.confidence_threshold < 1, \
            "confidence_threshold must be between 0 and 1"
        assert self.max_daily_loss > 0, "max_daily_loss must be positive"
        assert self.max_weekly_loss >= self.max_daily_loss, \
            "max_weekly_loss must be >= max_daily_loss"
        assert 0 < self.max_drawdown_percent < 1, \
            "max_drawdown_percent must be between 0 and 1"
        assert self.max_positions_per_market > 0, \
            "max_positions_per_market must be positive"
        assert self.max_total_positions > 0, \
            "max_total_positions must be positive"
        assert 0 < self.max_position_concentration < 1, \
            "max_position_concentration must be between 0 and 1"
        assert 0 < self.kelly_fraction <= 1, \
            "kelly_fraction must be between 0 and 1"


@dataclass
class APIConfig:
    """API and network configuration"""
    
    # Polymarket endpoints
    clob_host: str = "https://clob.polymarket.com"
    gamma_api: str = "https://gamma-api.polymarket.com"
    chain_id: int = 137  # Polygon mainnet
    signature_type: int = 1
    
    # API limits
    markets_fetch_limit: int = 100
    request_timeout: int = 30  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    
    # Circuit breaker
    circuit_breaker_threshold: int = 5  # failures before opening
    circuit_breaker_timeout: int = 300  # seconds before retry
    
    def validate(self) -> None:
        """Validate API configuration"""
        assert self.chain_id > 0, "chain_id must be positive"
        assert self.markets_fetch_limit > 0, "markets_fetch_limit must be positive"
        assert self.request_timeout > 0, "request_timeout must be positive"
        assert self.max_retries >= 0, "max_retries must be non-negative"
        assert self.circuit_breaker_threshold > 0, \
            "circuit_breaker_threshold must be positive"


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "polymarket_agent.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Metrics
    metrics_enabled: bool = True
    metrics_file: str = "metrics.json"
    
    # Alerts (placeholder for future webhook integration)
    alert_on_error: bool = True
    alert_on_large_loss: bool = True
    large_loss_threshold: float = 100.0
    
    def validate(self) -> None:
        """Validate monitoring configuration"""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert self.log_level in valid_log_levels, \
            f"log_level must be one of {valid_log_levels}"
        assert self.log_max_bytes > 0, "log_max_bytes must be positive"
        assert self.log_backup_count >= 0, "log_backup_count must be non-negative"


@dataclass
class AgentConfig:
    """Main agent configuration"""
    
    # Wallet
    private_key: str = field(default_factory=lambda: os.getenv("POLYGON_PRIVATE_KEY", ""))
    
    # Operating mode
    paper_trading: bool = True  # Start in paper trading mode by default
    
    # Cycle timing
    scan_interval_seconds: int = 300  # 5 minutes
    
    # Sub-configurations
    trading: TradingConfig = field(default_factory=TradingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    def validate(self) -> None:
        """Validate all configuration"""
        if not self.paper_trading and not self.private_key:
            raise ValueError(
                "POLYGON_PRIVATE_KEY environment variable required for live trading"
            )
        
        assert self.scan_interval_seconds > 0, \
            "scan_interval_seconds must be positive"
        
        # Validate sub-configurations
        self.trading.validate()
        self.api.validate()
        self.monitoring.validate()
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables"""
        config = cls(
            private_key=os.getenv("POLYGON_PRIVATE_KEY", ""),
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
            scan_interval_seconds=int(os.getenv("SCAN_INTERVAL", "300")),
        )
        
        # Trading config from env
        config.trading.min_liquidity = float(
            os.getenv("MIN_LIQUIDITY", str(config.trading.min_liquidity))
        )
        config.trading.max_position_size = float(
            os.getenv("MAX_POSITION_SIZE", str(config.trading.max_position_size))
        )
        config.trading.confidence_threshold = float(
            os.getenv("CONFIDENCE_THRESHOLD", str(config.trading.confidence_threshold))
        )
        config.trading.max_daily_loss = float(
            os.getenv("MAX_DAILY_LOSS", str(config.trading.max_daily_loss))
        )
        
        config.validate()
        return config


def load_config() -> AgentConfig:
    """Load and validate configuration"""
    config = AgentConfig.from_env()
    return config
