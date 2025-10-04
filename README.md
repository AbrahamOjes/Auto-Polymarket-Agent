# Polymarket Trading Agent 🤖

A production-ready autonomous trading agent for Polymarket that scans markets, analyzes opportunities, and executes trades with comprehensive risk management, monitoring, and testing capabilities.

## ✨ Features

### Core Trading
- 🔍 **Market Scanning**: Fetches and analyzes active markets from Polymarket's Gamma API
- 📊 **Opportunity Detection**: Identifies trading opportunities based on edge calculations
- 💰 **Smart Position Sizing**: Kelly Criterion-based position sizing with confidence adjustments
- 🎯 **Automated Execution**: Executes trades automatically when opportunities meet thresholds

### Risk Management
- 🛡️ **Multi-Layer Protection**:
  - Daily and weekly loss limits
  - Maximum drawdown protection
  - Position concentration limits
  - Per-market position limits
- 📉 **Real-time Monitoring**: Track P&L, drawdown, and risk metrics
- ⏸️ **Circuit Breakers**: Automatic trading halts on excessive losses

### Monitoring & Metrics
- 📈 **Performance Tracking**: Win rate, Sharpe ratio, P&L tracking
- 📊 **Detailed Metrics**: API performance, trade success rates, market scanning stats
- 📝 **Comprehensive Logging**: Rotating file logs with configurable levels
- 💾 **Persistent Storage**: Metrics and trade history saved to JSON

### Testing & Safety
- 🧪 **Paper Trading Mode**: Test strategies without risking real funds
- ✅ **Unit Tests**: Comprehensive test suite for core functionality
- 🔄 **Error Handling**: Robust error handling with automatic retries
- 🚨 **Circuit Breakers**: API circuit breakers to prevent cascading failures

## Prerequisites

- Python 3.8+
- Polygon wallet with MATIC for gas fees
- USDC balance on Polygon for trading

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd polymarket-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env and configure your settings
   ```

## ⚙️ Configuration

### Environment Variables

Edit the `.env` file with your configuration:

```bash
# Wallet Configuration (required for live trading)
POLYGON_PRIVATE_KEY=your_private_key_here

# Operating Mode
PAPER_TRADING=true  # Set to false for live trading

# Trading Parameters
MIN_LIQUIDITY=10000
MAX_POSITION_SIZE=100
CONFIDENCE_THRESHOLD=0.10
MAX_DAILY_LOSS=500

# Timing
SCAN_INTERVAL=300  # Seconds between market scans
```

### Advanced Configuration

For advanced configuration, modify `config.py`:

**Trading Configuration:**
- `min_liquidity`: Minimum market liquidity (default: 10,000 USDC)
- `max_position_size`: Maximum position size (default: 100 USDC)
- `min_position_size`: Minimum position size (default: 10 USDC)
- `confidence_threshold`: Minimum edge required (default: 10%)
- `max_daily_loss`: Maximum daily loss limit (default: 500 USDC)
- `max_weekly_loss`: Maximum weekly loss limit (default: 2,000 USDC)
- `max_drawdown_percent`: Maximum drawdown (default: 20%)
- `use_kelly_criterion`: Enable Kelly position sizing (default: true)
- `kelly_fraction`: Fraction of Kelly to use (default: 0.25)

**Risk Management:**
- `max_positions_per_market`: Max positions per market (default: 1)
- `max_total_positions`: Max total open positions (default: 10)
- `max_position_concentration`: Max portfolio concentration (default: 30%)

## 🚀 Usage

### Paper Trading (Recommended for Testing)

Start in paper trading mode to test without risking real funds:

```bash
python polymarket_agent_v2.py
```

The agent will:
1. Scan markets every 5 minutes (configurable)
2. Identify trading opportunities
3. Simulate trade execution
4. Track performance metrics
5. Log all activity to `polymarket_agent.log`

### Live Trading

⚠️ **WARNING**: Live trading involves real money. Only use funds you can afford to lose.

**Before going live, read the comprehensive [TESTING_GUIDE.md](TESTING_GUIDE.md)**

Quick steps:
1. Test in paper trading for 24-48 hours minimum
2. Set `PAPER_TRADING=false` in `.env`
3. Add your `POLYGON_PRIVATE_KEY`
4. Ensure your wallet has sufficient USDC and MATIC
5. Start with small position sizes
6. Run the agent:

```bash
python polymarket_agent_v2.py
```

**See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed production setup and safety procedures.**

### Running Tests

Run the comprehensive test suite:

```bash
# Run all tests
python test_agent.py

# Or using pytest
pytest test_agent.py -v

# With coverage
pytest test_agent.py --cov=. --cov-report=html
```

### Monitoring Performance

The agent provides real-time monitoring:

**Console Output:**
- Market scan results
- Opportunities found
- Trades executed
- Portfolio status updates

**Metrics Summary** (printed every 10 cycles):
```
📊 PORTFOLIO METRICS
  Current Balance:    $10,250.00
  Total P&L:          +$250.00
  Daily P&L:          +$50.00
  Win Rate:           65.00%

📈 TRADING METRICS
  Total Trades:       20
  Open Positions:     3
  Sharpe Ratio:       1.234
```

**Log Files:**
- `polymarket_agent.log`: Detailed activity log with rotation
- `metrics.json`: Performance metrics and trade history

## 📁 Project Structure

```
polymarket-agent/
├── polymarket_agent_v2.py    # Enhanced main agent
├── config.py                  # Configuration management
├── risk_manager.py            # Risk management system
├── metrics.py                 # Metrics collection
├── test_agent.py              # Unit tests
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
└── README.md                  # Documentation
```

## 🎯 Strategy Customization

The agent includes a placeholder for probability estimation. To implement your own strategy:

### 1. Modify the `_estimate_probability` method

In `polymarket_agent_v2.py`, update the `_estimate_probability` method:

```python
def _estimate_probability(self, market: Dict) -> float:
    """
    Implement your prediction model here:
    - News sentiment analysis
    - Historical data analysis
    - Expert forecasts aggregation
    - Statistical models
    - LLM-based reasoning
    """
    # Your custom logic here
    tokens = market.get("tokens", [])
    current_price = float(tokens[0].get("price", 0.5))
    
    # Example: Add your edge calculation
    your_estimated_probability = current_price + 0.05  # Replace with your model
    
    return your_estimated_probability
```

### 2. Integrate External Data Sources

Add data sources for better predictions:
- News APIs (NewsAPI, Google News)
- Social media sentiment (Twitter, Reddit)
- Historical market data
- Expert predictions
- Weather data (for weather markets)
- Sports statistics (for sports markets)

### 3. Implement Machine Learning Models

Consider implementing:
- Logistic regression for binary outcomes
- Time series models for trending markets
- Ensemble methods combining multiple signals
- Neural networks for complex patterns

## Risk Warning

This is experimental software. Use at your own risk. Cryptocurrency trading involves substantial risk of loss. Only trade with funds you can afford to lose.

## License

MIT
