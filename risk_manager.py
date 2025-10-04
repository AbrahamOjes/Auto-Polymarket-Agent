"""
Risk management system for Polymarket Trading Agent
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a single trade"""
    timestamp: datetime
    market_id: str
    market_title: str
    side: str
    amount: float
    token_id: str
    price: float
    pnl: Optional[float] = None
    status: str = "open"  # open, closed, failed


@dataclass
class Position:
    """Current position in a market"""
    market_id: str
    market_title: str
    token_id: str
    side: str
    amount: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class RiskManager:
    """Manages risk limits and position tracking"""
    
    def __init__(self, config):
        """
        Initialize risk manager
        
        Args:
            config: TradingConfig instance
        """
        self.config = config
        
        # Track trades and positions
        self.trades: List[Trade] = []
        self.positions: Dict[str, Position] = {}
        
        # Track P&L
        self.daily_pnl: Dict[str, float] = defaultdict(float)  # date -> pnl
        self.weekly_pnl: Dict[str, float] = defaultdict(float)  # week -> pnl
        self.total_pnl: float = 0.0
        self.peak_balance: float = 0.0
        self.initial_balance: float = 0.0
        
        # Circuit breaker state
        self.consecutive_losses: int = 0
        self.is_halted: bool = False
        self.halt_until: Optional[datetime] = None
        
        logger.info("Risk Manager initialized")
    
    def set_initial_balance(self, balance: float) -> None:
        """Set initial balance for drawdown calculation"""
        self.initial_balance = balance
        self.peak_balance = balance
        logger.info(f"Initial balance set to ${balance:.2f}")
    
    def can_trade(self, amount: float, market_id: str) -> tuple[bool, str]:
        """
        Check if a trade is allowed based on risk limits
        
        Returns:
            (allowed, reason) tuple
        """
        # Check if trading is halted
        if self.is_halted:
            if self.halt_until and datetime.now() < self.halt_until:
                return False, f"Trading halted until {self.halt_until}"
            else:
                self.is_halted = False
                self.halt_until = None
                logger.info("Trading halt lifted")
        
        # Check daily loss limit
        today = datetime.now().date().isoformat()
        if abs(self.daily_pnl[today]) >= self.config.max_daily_loss:
            self._halt_trading(reason="Daily loss limit reached")
            return False, f"Daily loss limit reached: ${abs(self.daily_pnl[today]):.2f}"
        
        # Check weekly loss limit
        week = self._get_week_key()
        if abs(self.weekly_pnl[week]) >= self.config.max_weekly_loss:
            self._halt_trading(reason="Weekly loss limit reached")
            return False, f"Weekly loss limit reached: ${abs(self.weekly_pnl[week]):.2f}"
        
        # Check drawdown
        current_balance = self.initial_balance + self.total_pnl
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if drawdown >= self.config.max_drawdown_percent:
            self._halt_trading(reason="Maximum drawdown reached")
            return False, f"Max drawdown reached: {drawdown:.2%}"
        
        # Check position limits
        if len(self.positions) >= self.config.max_total_positions:
            return False, f"Max total positions reached: {len(self.positions)}"
        
        # Check per-market position limit
        market_positions = sum(
            1 for p in self.positions.values() if p.market_id == market_id
        )
        if market_positions >= self.config.max_positions_per_market:
            return False, f"Max positions per market reached for {market_id}"
        
        # Check position concentration
        total_exposure = sum(p.amount for p in self.positions.values())
        if total_exposure > 0:
            new_concentration = (amount + total_exposure) / (current_balance if current_balance > 0 else self.initial_balance)
            if new_concentration > self.config.max_position_concentration:
                return False, f"Position concentration too high: {new_concentration:.2%}"
        
        # Check position size limits
        if amount < self.config.min_position_size:
            return False, f"Position size too small: ${amount:.2f}"
        
        if amount > self.config.max_position_size:
            return False, f"Position size too large: ${amount:.2f}"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        edge: float,
        price: float,
        confidence: float
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        
        Args:
            edge: Expected edge (probability advantage)
            price: Current market price
            confidence: Confidence in the prediction (0-1)
        
        Returns:
            Recommended position size in USDC
        """
        if not self.config.use_kelly_criterion:
            return self.config.max_position_size
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds, p = win probability, q = loss probability
        
        # Calculate win probability and odds
        if edge > 0:  # Buying YES
            win_prob = price + edge
            odds = (1 - price) / price if price > 0 else 0
        else:  # Buying NO
            win_prob = 1 - (price + edge)
            odds = price / (1 - price) if price < 1 else 0
        
        loss_prob = 1 - win_prob
        
        # Kelly fraction
        if odds > 0:
            kelly = (odds * win_prob - loss_prob) / odds
        else:
            kelly = 0
        
        # Apply Kelly fraction and confidence adjustment
        kelly = max(0, kelly) * self.config.kelly_fraction * confidence
        
        # Calculate position size
        current_balance = self.initial_balance + self.total_pnl
        position_size = kelly * current_balance
        
        # Clamp to min/max limits
        position_size = max(self.config.min_position_size, position_size)
        position_size = min(self.config.max_position_size, position_size)
        
        logger.debug(
            f"Kelly position sizing: edge={edge:.3f}, price={price:.3f}, "
            f"kelly={kelly:.3f}, size=${position_size:.2f}"
        )
        
        return position_size
    
    def record_trade(
        self,
        market_id: str,
        market_title: str,
        token_id: str,
        side: str,
        amount: float,
        price: float,
        status: str = "open"
    ) -> Trade:
        """Record a new trade"""
        trade = Trade(
            timestamp=datetime.now(),
            market_id=market_id,
            market_title=market_title,
            side=side,
            amount=amount,
            token_id=token_id,
            price=price,
            status=status
        )
        
        self.trades.append(trade)
        
        # Create or update position
        if status == "open":
            self.positions[market_id] = Position(
                market_id=market_id,
                market_title=market_title,
                token_id=token_id,
                side=side,
                amount=amount,
                entry_price=price,
                current_price=price
            )
        
        logger.info(
            f"Trade recorded: {side} ${amount:.2f} in {market_title} @ {price:.3f}"
        )
        
        return trade
    
    def update_position(
        self,
        market_id: str,
        current_price: float
    ) -> None:
        """Update position with current market price"""
        if market_id not in self.positions:
            return
        
        position = self.positions[market_id]
        position.current_price = current_price
        
        # Calculate unrealized P&L
        if position.side == "BUY":
            position.unrealized_pnl = (current_price - position.entry_price) * position.amount
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.amount
    
    def close_position(
        self,
        market_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Optional[float]:
        """
        Close a position and record P&L
        
        Returns:
            Realized P&L
        """
        if market_id not in self.positions:
            logger.warning(f"Cannot close position: {market_id} not found")
            return None
        
        position = self.positions[market_id]
        
        # Calculate realized P&L
        if position.side == "BUY":
            pnl = (exit_price - position.entry_price) * position.amount
        else:
            pnl = (position.entry_price - exit_price) * position.amount
        
        # Update P&L tracking
        self.total_pnl += pnl
        today = datetime.now().date().isoformat()
        self.daily_pnl[today] += pnl
        week = self._get_week_key()
        self.weekly_pnl[week] += pnl
        
        # Track consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Remove position
        del self.positions[market_id]
        
        logger.info(
            f"Position closed: {position.market_title} | "
            f"P&L: ${pnl:.2f} | Reason: {reason}"
        )
        
        return pnl
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary"""
        current_balance = self.initial_balance + self.total_pnl
        drawdown = 0.0
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
        
        today = datetime.now().date().isoformat()
        week = self._get_week_key()
        
        return {
            "current_balance": current_balance,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl[today],
            "weekly_pnl": self.weekly_pnl[week],
            "drawdown": drawdown,
            "peak_balance": self.peak_balance,
            "open_positions": len(self.positions),
            "total_trades": len(self.trades),
            "consecutive_losses": self.consecutive_losses,
            "is_halted": self.is_halted
        }
    
    def _halt_trading(self, reason: str, duration_seconds: int = 3600) -> None:
        """Halt trading for a specified duration"""
        self.is_halted = True
        self.halt_until = datetime.now() + timedelta(seconds=duration_seconds)
        logger.warning(
            f"Trading halted: {reason}. Will resume at {self.halt_until}"
        )
    
    def _get_week_key(self) -> str:
        """Get week identifier (year-week)"""
        now = datetime.now()
        return f"{now.year}-W{now.isocalendar()[1]}"
