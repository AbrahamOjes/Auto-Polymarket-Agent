"""
Autonomous Polymarket Trading Agent
Scans markets, analyzes opportunities, and executes trades autonomously
"""

import os
import time
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolymarketAgent:
    """Autonomous agent for discovering and trading on Polymarket"""

    def __init__(
        self,
        private_key: str,
        min_liquidity: float = 10000,
        max_position_size: float = 100,
        confidence_threshold: float = 0.15
    ):
        """
        Initialize the Polymarket trading agent

        Args:
            private_key: Wallet private key
            min_liquidity: Minimum market liquidity to consider
            max_position_size: Maximum USDC per trade
            confidence_threshold: Minimum edge required to trade
        """
        self.clob_client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,  # Polygon mainnet
            signature_type=1
        )

        # Set API credentials
        self.clob_client.set_api_creds(
            self.clob_client.create_or_derive_api_creds()
        )

        self.gamma_api = "https://gamma-api.polymarket.com"
        self.min_liquidity = min_liquidity
        self.max_position_size = max_position_size
        self.confidence_threshold = confidence_threshold

        logger.info("Polymarket Agent initialized")

    def get_markets(self, limit: int = 100) -> List[Dict]:
        """
        Fetch active markets from Polymarket Gamma API

        Returns:
            List of market dictionaries
        """
        try:
            response = requests.get(
                f"{self.gamma_api}/markets",
                params={"limit": limit, "active": True}
            )
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} active markets")
            return markets
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    def get_market_details(self, condition_id: str) -> Optional[Dict]:
        """Get detailed information about a specific market"""
        try:
            response = requests.get(
                f"{self.gamma_api}/markets/{condition_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market {condition_id}: {e}")
            return None

    def analyze_market(self, market: Dict) -> Dict:
        """
        Analyze market for trading opportunities

        Returns:
            Analysis dict with opportunity score and recommended action
        """
        analysis = {
            "market_id": market.get("condition_id"),
            "title": market.get("question"),
            "opportunity": False,
            "side": None,
            "confidence": 0.0,
            "expected_value": 0.0
        }

        # Skip if insufficient liquidity
        liquidity = market.get("liquidity", 0)
        if liquidity < self.min_liquidity:
            return analysis

        # Get current market prices
        tokens = market.get("tokens", [])
        if len(tokens) < 2:
            return analysis

        yes_price = float(tokens[0].get("price", 0))
        no_price = float(tokens[1].get("price", 0))

        # Calculate expected probabilities (this is where you'd add your model)
        estimated_yes_prob = self._estimate_probability(market)

        # Calculate edge
        market_yes_prob = yes_price
        edge = estimated_yes_prob - market_yes_prob

        # Determine if there's an opportunity
        if abs(edge) > self.confidence_threshold:
            analysis["opportunity"] = True
            analysis["side"] = BUY if edge > 0 else SELL
            analysis["confidence"] = abs(edge)
            analysis["expected_value"] = self._calculate_ev(
                edge, yes_price, no_price
            )

            logger.info(
                f"Opportunity found: {market.get('question')}\n"
                f"  Edge: {edge:.2%}, EV: ${analysis['expected_value']:.2f}"
            )

        return analysis

    def _estimate_probability(self, market: Dict) -> float:
        """
        Estimate true probability of event occurring

        This is where you'd implement your prediction model:
        - News sentiment analysis
        - Historical data analysis
        - Expert forecasts aggregation
        - Statistical models
        - LLM-based reasoning

        For now, returns market price (no edge)
        """
        # PLACEHOLDER: Implement your prediction logic here
        tokens = market.get("tokens", [])
        if tokens:
            return float(tokens[0].get("price", 0.5))
        return 0.5

    def _calculate_ev(
        self,
        edge: float,
        yes_price: float,
        no_price: float
    ) -> float:
        """Calculate expected value of trade"""
        if edge > 0:  # Buying YES
            win_amount = (1 - yes_price) * self.max_position_size
            loss_amount = yes_price * self.max_position_size
            prob_win = yes_price + edge
        else:  # Buying NO (selling YES)
            win_amount = yes_price * self.max_position_size
            loss_amount = (1 - yes_price) * self.max_position_size
            prob_win = 1 - (yes_price + edge)

        ev = (prob_win * win_amount) - ((1 - prob_win) * loss_amount)
        return ev

    def execute_trade(
        self,
        token_id: str,
        side: str,
        amount: float
    ) -> Optional[Dict]:
        """
        Execute a market order

        Args:
            token_id: Market token ID
            side: BUY or SELL
            amount: USDC amount to trade

        Returns:
            Trade response or None if failed
        """
        try:
            order = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=side,
                order_type=OrderType.FOK  # Fill-or-kill
            )

            signed_order = self.clob_client.create_market_order(order)
            response = self.clob_client.post_order(
                signed_order,
                OrderType.FOK
            )

            logger.info(f"Trade executed: {response}")
            return response

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return None

    def run_cycle(self):
        """Run one cycle of market scanning and trading"""
        logger.info("Starting market scan cycle...")

        # Fetch active markets
        markets = self.get_markets(limit=100)

        # Analyze each market
        opportunities = []
        for market in markets:
            analysis = self.analyze_market(market)
            if analysis["opportunity"]:
                opportunities.append(analysis)

        # Sort by expected value
        opportunities.sort(
            key=lambda x: x["expected_value"],
            reverse=True
        )

        # Execute top opportunities (respecting position limits)
        for opp in opportunities[:5]:  # Top 5 opportunities
            logger.info(f"Executing trade for: {opp['title']}")

            # Get token_id from market
            market = self.get_market_details(opp["market_id"])
            if not market:
                continue

            token_id = market["tokens"][0]["token_id"]

            # Execute trade
            self.execute_trade(
                token_id=token_id,
                side=opp["side"],
                amount=min(opp["expected_value"], self.max_position_size)
            )

            # Rate limiting
            time.sleep(2)

        logger.info(f"Cycle complete. Found {len(opportunities)} opportunities")

    def run_continuous(self, interval_seconds: int = 300):
        """
        Run agent continuously

        Args:
            interval_seconds: Seconds between market scans
        """
        logger.info("Starting autonomous trading agent...")

        while True:
            try:
                self.run_cycle()
                logger.info(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("Agent stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying


def main():
    """Example usage"""
    # Load environment variables
    load_dotenv()
    
    # Configuration
    PRIVATE_KEY = os.getenv("POLYGON_PRIVATE_KEY")

    if not PRIVATE_KEY:
        raise ValueError("POLYGON_PRIVATE_KEY environment variable required")

    # Initialize agent
    agent = PolymarketAgent(
        private_key=PRIVATE_KEY,
        min_liquidity=10000,
        max_position_size=100,
        confidence_threshold=0.10  # 10% edge required
    )

    # Run continuously
    agent.run_continuous(interval_seconds=300)  # Check every 5 minutes


if __name__ == "__main__":
    main()
