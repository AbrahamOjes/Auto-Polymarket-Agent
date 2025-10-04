# Quick Reference Card 📋

## 🚀 Common Commands

### Start Agent
```bash
# Paper trading (safe)
python polymarket_agent_v2.py

# Production (real money - be careful!)
# Set PAPER_TRADING=false in .env first
python polymarket_agent_v2.py
```

### Run Tests
```bash
python test_agent.py
```

### Check Logs
```bash
# View recent logs
tail -50 polymarket_agent.log

# Follow logs in real-time
tail -f polymarket_agent.log

# Search for errors
grep ERROR polymarket_agent.log
```

### Check Metrics
```bash
# View metrics
cat metrics.json | python -m json.tool

# Check latest performance
cat metrics.json | python -m json.tool | grep -A 20 "latest_snapshot"
```

---

## ⚙️ Configuration Quick Reference

### Environment Variables (.env)

```bash
# Operating Mode
PAPER_TRADING=true              # true = safe testing, false = real money

# Wallet (required for live trading)
POLYGON_PRIVATE_KEY=your_key    # Keep secret!

# Trading Parameters
MIN_LIQUIDITY=10000             # Minimum market liquidity
MAX_POSITION_SIZE=100           # Max $ per trade
CONFIDENCE_THRESHOLD=0.10       # Min edge required (10%)
MAX_DAILY_LOSS=500              # Stop after this daily loss

# Timing
SCAN_INTERVAL=300               # Seconds between scans (5 min)
```

### Conservative Settings (Recommended for Production Start)

```bash
PAPER_TRADING=false
MAX_POSITION_SIZE=25            # Start small!
CONFIDENCE_THRESHOLD=0.15       # Higher = fewer trades
MAX_DAILY_LOSS=100              # Conservative limit
SCAN_INTERVAL=600               # Less frequent (10 min)
```

---

## 🛡️ Risk Limits (config.py)

| Limit | Default | Purpose |
|-------|---------|---------|
| Daily Loss | $500 | Stop trading after daily loss |
| Weekly Loss | $2,000 | Stop trading after weekly loss |
| Max Drawdown | 20% | Halt at 20% from peak |
| Min Position | $10 | Minimum trade size |
| Max Position | $100 | Maximum trade size |
| Max Positions | 10 | Total open positions |
| Position Concentration | 30% | Max % in single market |

---

## 📊 Monitoring Checklist

### Every Hour (First 24h)
- [ ] Check console output
- [ ] Verify trades executing correctly
- [ ] No errors in logs

### Daily
- [ ] Review `polymarket_agent.log`
- [ ] Check `metrics.json` performance
- [ ] Verify wallet balance
- [ ] Check open positions on Polymarket

### Weekly
- [ ] Analyze win rate and Sharpe ratio
- [ ] Review and adjust parameters
- [ ] Backup logs and metrics
- [ ] Optimize strategy if needed

---

## 🚨 Emergency Actions

### Stop Agent Immediately
```bash
# Press Ctrl+C in terminal
# Or find and kill process:
ps aux | grep polymarket_agent_v2.py
kill <PID>
```

### Check What Went Wrong
```bash
# View recent errors
tail -100 polymarket_agent.log | grep ERROR

# Check last trades
tail -50 polymarket_agent.log | grep "TRADE"

# Review metrics
cat metrics.json | python -m json.tool
```

### Close Positions Manually
1. Go to https://polymarket.com
2. Connect your wallet
3. View open positions
4. Close each position manually

---

## 📁 Important Files

| File | Purpose | Location |
|------|---------|----------|
| `.env` | Configuration | Root directory |
| `polymarket_agent.log` | Detailed logs | Root directory |
| `metrics.json` | Performance data | Root directory |
| `config.py` | Advanced config | Root directory |
| `test_agent.py` | Unit tests | Root directory |

---

## 🎯 Testing Environments

| Environment | Real Money | Command |
|-------------|------------|---------|
| **Paper Trading** | ❌ No | `PAPER_TRADING=true` |
| **Production** | ✅ Yes | `PAPER_TRADING=false` |

⚠️ **Always start with paper trading!**

---

## 📈 Performance Metrics

### Good Indicators
- ✅ Win rate > 55%
- ✅ Sharpe ratio > 1.0
- ✅ Consistent positive P&L
- ✅ Low API error rate
- ✅ Risk limits working

### Warning Signs
- 🚨 Win rate < 45%
- 🚨 Large drawdowns
- 🚨 Frequent API errors
- 🚨 Risk limits not enforcing
- 🚨 Unexpected behavior

---

## 🔧 Troubleshooting

### "No markets fetched"
```bash
# Check internet
ping gamma-api.polymarket.com

# Check API
curl https://gamma-api.polymarket.com/markets?limit=1
```

### "Trade execution failed"
- Check wallet MATIC balance (need for gas)
- Check wallet USDC balance
- Verify private key in `.env`
- Check Polygon network status

### "Circuit breaker open"
- Normal after API failures
- Wait 5 minutes for reset
- Check logs for root cause

### Agent crashes
```bash
# Check logs
tail -100 polymarket_agent.log

# Run tests
python test_agent.py

# Verify config
python -c "from config import load_config; load_config().validate()"
```

---

## 📚 Documentation

| Guide | Purpose |
|-------|---------|
| `README.md` | Main documentation |
| `QUICKSTART.md` | 5-minute setup |
| `TESTING_GUIDE.md` | **Sandbox & production testing** |
| `IMPROVEMENTS.md` | Features breakdown |
| `ARCHITECTURE.md` | System design |

---

## ✅ Pre-Flight Checklist

### Before Paper Trading
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created and configured
- [ ] `PAPER_TRADING=true` in `.env`
- [ ] Tests passing (`python test_agent.py`)

### Before Production
- [ ] Paper trading tested 24+ hours
- [ ] Strategy shows positive results
- [ ] Wallet has MATIC (5-10 MATIC)
- [ ] Wallet has USDC for trading
- [ ] `PAPER_TRADING=false` in `.env`
- [ ] `POLYGON_PRIVATE_KEY` set in `.env`
- [ ] Conservative risk limits set
- [ ] Monitoring plan in place
- [ ] Know how to stop agent
- [ ] Read TESTING_GUIDE.md

---

## 💡 Quick Tips

1. **Start Small**: Use small position sizes initially
2. **Monitor Closely**: Check frequently in first 24 hours
3. **Be Patient**: Don't rush to production
4. **Keep Records**: Backup logs and metrics regularly
5. **Stay Informed**: Monitor Polymarket and crypto news
6. **Have Limits**: Set strict risk limits
7. **Be Ready**: Know how to stop and intervene
8. **Learn**: Analyze performance and optimize

---

## 🔗 Useful Links

- **Polymarket**: https://polymarket.com
- **Polygonscan**: https://polygonscan.com
- **Polygon Status**: https://status.polygon.technology
- **Your Wallet**: https://polygonscan.com/address/YOUR_ADDRESS

---

## 📞 Getting Help

1. Check logs: `tail -f polymarket_agent.log`
2. Review metrics: `cat metrics.json`
3. Run tests: `python test_agent.py`
4. Read docs: `README.md`, `TESTING_GUIDE.md`
5. Check Polymarket Discord

---

**Remember: Only risk what you can afford to lose! 🛡️**
