# Quick Start Guide 🚀

Get your Polymarket trading agent up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file
# For testing, leave PAPER_TRADING=true
# For live trading, set PAPER_TRADING=false and add your private key
```

## Step 3: Run Tests (Optional but Recommended)

```bash
# Run unit tests to verify everything works
python test_agent.py
```

## Step 4: Start Paper Trading

```bash
# Start the agent in paper trading mode
python polymarket_agent_v2.py
```

You should see output like:

```
============================================================
STARTING AUTONOMOUS TRADING AGENT
============================================================
Mode: PAPER TRADING
Scan Interval: 300s
Press Ctrl+C to stop
============================================================

Starting market scan cycle...
Fetched 100 active markets
Scan complete: 100 markets, 5 opportunities found

Attempting trade 1: Will Bitcoin reach $100k by end of 2024?...
[PAPER TRADE] BUY $45.23 in Will Bitcoin reach $100k... @ 0.523

Portfolio Status:
  Balance: $10,000.00
  Total P&L: $0.00
  Daily P&L: $0.00
  Open Positions: 1
  Drawdown: 0.00%
```

## Step 5: Monitor Performance

The agent will:
- ✅ Scan markets every 5 minutes
- ✅ Log all activity to `polymarket_agent.log`
- ✅ Save metrics to `metrics.json`
- ✅ Print performance summary every 10 cycles

## What's Next?

### Customize Your Strategy

Edit `polymarket_agent_v2.py` and modify the `_estimate_probability` method:

```python
def _estimate_probability(self, market: Dict) -> float:
    # Add your prediction logic here
    # Example: Use news sentiment, historical data, etc.
    return your_probability_estimate
```

### Adjust Risk Parameters

Edit `.env` to change:
- `MAX_POSITION_SIZE`: Maximum $ per trade
- `CONFIDENCE_THRESHOLD`: Minimum edge required
- `MAX_DAILY_LOSS`: Stop trading after this loss
- `SCAN_INTERVAL`: Time between market scans

### Go Live (When Ready)

⚠️ **Only after thorough testing!**

1. Set `PAPER_TRADING=false` in `.env`
2. Add your `POLYGON_PRIVATE_KEY`
3. Ensure wallet has USDC and MATIC
4. Start the agent: `python polymarket_agent_v2.py`

## Troubleshooting

### "No markets fetched"
- Check internet connection
- Verify Polymarket API is accessible
- Check logs for detailed error messages

### "Circuit breaker open"
- API is experiencing issues
- Wait for timeout (default 5 minutes)
- Check `polymarket_agent.log` for details

### "Trading halted"
- Risk limit reached (daily loss, drawdown, etc.)
- Check portfolio summary in logs
- Adjust risk parameters if needed

## Getting Help

- Check `polymarket_agent.log` for detailed logs
- Review `metrics.json` for performance data
- Read the full README.md for comprehensive documentation

## Safety Reminders

✅ **Always start with paper trading**
✅ **Test your strategy thoroughly**
✅ **Start with small position sizes**
✅ **Monitor the agent regularly**
✅ **Only risk what you can afford to lose**

Happy trading! 🎯
