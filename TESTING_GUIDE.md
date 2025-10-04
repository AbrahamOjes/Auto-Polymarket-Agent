# Testing Guide: Sandbox & Production 🧪

This guide explains how to test your Polymarket Trading Agent in different environments.

---

## 🎯 Testing Environments Overview

| Environment | Real Money | Real Markets | Purpose |
|-------------|------------|--------------|---------|
| **Paper Trading** | ❌ No | ✅ Yes | Strategy testing, safe development |
| **Polygon Mumbai (Testnet)** | ❌ No | ⚠️ Limited | Blockchain testing with test tokens |
| **Polygon Mainnet (Production)** | ✅ Yes | ✅ Yes | Live trading with real money |

---

## 1️⃣ Paper Trading (Recommended First Step)

### What It Is
- Simulates trades without executing on blockchain
- Uses real market data from Polymarket
- Tracks performance as if trading were real
- **Zero risk** - no real money involved

### Setup

```bash
# 1. Configure for paper trading
cp .env.example .env

# 2. Edit .env - ensure these settings:
PAPER_TRADING=true
POLYGON_PRIVATE_KEY=  # Can be empty for paper trading

# 3. Run the agent
python polymarket_agent_v2.py
```

### What You'll See

```
============================================================
STARTING AUTONOMOUS TRADING AGENT
============================================================
Mode: PAPER TRADING  ← Confirms paper trading mode
Scan Interval: 300s
============================================================

[PAPER TRADE] BUY $45.23 in Will Bitcoin reach $100k...
                ↑
         Paper trade indicator
```

### Testing Checklist

- ✅ Agent starts without errors
- ✅ Markets are fetched successfully
- ✅ Opportunities are identified
- ✅ Trades are simulated (marked as [PAPER TRADE])
- ✅ Risk limits are enforced
- ✅ Metrics are collected
- ✅ Logs are created

### Duration
**Recommended: 24-48 hours minimum**

Monitor for:
- Strategy performance
- Risk management behavior
- API reliability
- Error handling

---

## 2️⃣ Polygon Mumbai Testnet (Optional)

### What It Is
- Polygon's test network
- Uses test MATIC (free from faucets)
- **Note**: Polymarket doesn't have a testnet deployment
- Useful for testing blockchain interactions only

### Limitations
⚠️ **Polymarket operates only on Polygon Mainnet**
- No test markets available
- Cannot test actual Polymarket trading
- Only useful for testing wallet/blockchain functionality

### Setup (If Testing Blockchain Only)

```bash
# 1. Get Mumbai testnet MATIC
# Visit: https://faucet.polygon.technology/

# 2. Configure for Mumbai
# Edit polymarket_agent_v2.py, change:
chain_id=80001  # Mumbai testnet (instead of 137)

# 3. Update .env
POLYGON_PRIVATE_KEY=your_testnet_wallet_key
PAPER_TRADING=false
```

### Use Case
- Test wallet connectivity
- Test transaction signing
- Test gas fee estimation
- **Not for testing Polymarket trading**

---

## 3️⃣ Polygon Mainnet Production (Real Money)

### ⚠️ WARNING: Real Money at Risk

This is **live trading** with real USDC on Polygon mainnet.

### Prerequisites

Before going live:

1. **✅ Paper Trading Success**
   - Tested for 24-48 hours minimum
   - Strategy shows positive results
   - No critical errors

2. **✅ Wallet Preparation**
   - Polygon wallet with private key
   - Sufficient MATIC for gas fees (~5-10 MATIC recommended)
   - USDC balance for trading (start small!)

3. **✅ Risk Understanding**
   - Understand all risk parameters
   - Know how to stop the agent
   - Prepared to monitor regularly

4. **✅ Configuration Review**
   - Risk limits are appropriate
   - Position sizes are conservative
   - Confidence threshold is reasonable

### Step-by-Step Production Setup

#### Step 1: Prepare Your Wallet

```bash
# Get your wallet ready:
# 1. Create/use existing Polygon wallet
# 2. Fund with MATIC (for gas fees)
# 3. Fund with USDC (for trading)

# Check balances:
# - Visit: https://polygonscan.com/
# - Enter your wallet address
# - Verify MATIC and USDC balances
```

#### Step 2: Configure Environment

```bash
# Edit .env file
nano .env
```

```bash
# PRODUCTION CONFIGURATION
POLYGON_PRIVATE_KEY=your_actual_private_key_here  # ⚠️ Keep secret!
PAPER_TRADING=false  # ⚠️ This enables live trading

# Start with conservative settings
MIN_LIQUIDITY=50000  # Higher liquidity = safer
MAX_POSITION_SIZE=50  # Start small!
CONFIDENCE_THRESHOLD=0.15  # Higher threshold = fewer trades
MAX_DAILY_LOSS=100  # Conservative limit
SCAN_INTERVAL=600  # Scan every 10 minutes (less aggressive)
```

#### Step 3: Verify Configuration

```bash
# Test configuration loading
python -c "from config import load_config; c = load_config(); print(f'Paper Trading: {c.paper_trading}'); print(f'Max Position: ${c.trading.max_position_size}')"

# Expected output:
# Paper Trading: False  ← Should be False for production
# Max Position: $50.0
```

#### Step 4: Start with Dry Run

Before going live, do a final check:

```bash
# 1. Run tests
python test_agent.py

# 2. Check logs are working
ls -lh polymarket_agent.log

# 3. Verify metrics file
cat metrics.json
```

#### Step 5: Start Production Trading

```bash
# Start the agent
python polymarket_agent_v2.py

# You should see:
# Mode: LIVE TRADING  ← Confirms production mode
# Initial Balance: $XXX.XX
```

#### Step 6: Monitor Closely

**First Hour:**
- Watch console output continuously
- Check every trade execution
- Verify trades on Polymarket UI

**First 24 Hours:**
- Check every 2-4 hours
- Review logs for errors
- Monitor P&L and positions

**Ongoing:**
- Daily check-ins minimum
- Review metrics weekly
- Adjust parameters as needed

---

## 🛡️ Production Safety Checklist

### Before Starting

- [ ] Paper trading tested for 24+ hours
- [ ] All tests passing (`python test_agent.py`)
- [ ] Wallet has sufficient MATIC (5-10 MATIC)
- [ ] Wallet has USDC for trading
- [ ] Private key is secure and backed up
- [ ] `.env` file is in `.gitignore`
- [ ] Risk limits are set conservatively
- [ ] You understand how to stop the agent (Ctrl+C)
- [ ] You have monitoring plan in place

### During Operation

- [ ] Monitor console output regularly
- [ ] Check `polymarket_agent.log` for errors
- [ ] Review `metrics.json` for performance
- [ ] Verify trades on Polymarket website
- [ ] Watch for unusual behavior
- [ ] Be ready to intervene if needed

### Red Flags to Watch For

🚨 **Stop the agent immediately if:**
- Unexpected large losses
- Repeated trade failures
- API errors increasing
- Risk limits not being enforced
- Strange market behavior
- Wallet balance discrepancies

---

## 📊 Monitoring Production

### Real-Time Monitoring

```bash
# Watch logs in real-time
tail -f polymarket_agent.log

# Monitor metrics
watch -n 60 'cat metrics.json | python -m json.tool | grep -A 5 "latest_snapshot"'
```

### Check Wallet Balance

```bash
# Visit Polygonscan
https://polygonscan.com/address/YOUR_WALLET_ADDRESS

# Or use web3 tools
# (You can add balance checking to the agent)
```

### Verify Trades on Polymarket

```bash
# Visit your Polymarket profile
https://polymarket.com/profile/YOUR_WALLET_ADDRESS

# Check:
# - Open positions
# - Trade history
# - P&L
```

---

## 🔄 Progressive Testing Strategy

### Recommended Approach

```
Week 1: Paper Trading
├─ Day 1-2: Initial testing, fix any issues
├─ Day 3-5: Strategy validation
└─ Day 6-7: Performance analysis

Week 2: Small Production Test
├─ MAX_POSITION_SIZE=25
├─ MAX_DAILY_LOSS=50
├─ CONFIDENCE_THRESHOLD=0.20
└─ Monitor closely

Week 3: Gradual Scale-Up
├─ Increase position size if successful
├─ Adjust parameters based on results
└─ Continue monitoring

Week 4+: Full Production
├─ Normal parameters
├─ Regular monitoring
└─ Continuous optimization
```

---

## 🧪 Testing Scenarios

### Scenario 1: Strategy Validation (Paper Trading)

**Goal**: Validate your prediction model works

```bash
# Run for 48 hours in paper trading
PAPER_TRADING=true
CONFIDENCE_THRESHOLD=0.10  # Lower threshold for more trades

# Monitor:
# - Win rate (target: >55%)
# - Sharpe ratio (target: >1.0)
# - Number of opportunities found
```

### Scenario 2: Risk Management Testing (Paper Trading)

**Goal**: Verify risk limits work correctly

```bash
# Set aggressive limits to trigger them
MAX_DAILY_LOSS=50
MAX_POSITION_SIZE=100

# Verify:
# - Trading halts when daily loss reached
# - Position sizes are capped
# - Drawdown protection works
```

### Scenario 3: Small Production Test

**Goal**: Test with minimal real money

```bash
PAPER_TRADING=false
MAX_POSITION_SIZE=10  # Very small
MAX_DAILY_LOSS=25
CONFIDENCE_THRESHOLD=0.25  # Very conservative

# Run for 24 hours
# Expected: 1-3 trades maximum
```

### Scenario 4: Full Production

**Goal**: Normal trading operations

```bash
PAPER_TRADING=false
MAX_POSITION_SIZE=100
MAX_DAILY_LOSS=500
CONFIDENCE_THRESHOLD=0.10

# Monitor daily
# Adjust based on performance
```

---

## 🔧 Troubleshooting

### Issue: "No markets fetched"

```bash
# Check internet connection
ping gamma-api.polymarket.com

# Check API status
curl https://gamma-api.polymarket.com/markets?limit=1

# Review logs
tail -50 polymarket_agent.log
```

### Issue: "Trade execution failed"

**Paper Trading:**
- Check logs for specific error
- Verify market data is valid

**Production:**
- Check wallet MATIC balance (need gas)
- Check wallet USDC balance
- Verify private key is correct
- Check Polygon network status

### Issue: "Circuit breaker open"

```bash
# This is normal after repeated API failures
# Wait for timeout (default 5 minutes)
# Check logs for root cause

grep "Circuit breaker" polymarket_agent.log
```

### Issue: Unexpected behavior

```bash
# 1. Stop the agent immediately
Ctrl+C

# 2. Review recent logs
tail -100 polymarket_agent.log

# 3. Check metrics
cat metrics.json | python -m json.tool

# 4. Verify configuration
python -c "from config import load_config; load_config().validate()"
```

---

## 📈 Performance Benchmarks

### Paper Trading Expectations

After 24 hours, you should see:
- Markets scanned: 200-500
- Opportunities found: 10-50 (depends on threshold)
- Trades executed: 5-20
- Win rate: Varies by strategy
- No errors or crashes

### Production Expectations

First week:
- Start conservative (few trades)
- Focus on reliability over profit
- Verify all systems work correctly
- Build confidence gradually

---

## 🎓 Best Practices

### 1. Start Small
```bash
# Week 1
MAX_POSITION_SIZE=25

# Week 2 (if successful)
MAX_POSITION_SIZE=50

# Week 3+ (if successful)
MAX_POSITION_SIZE=100
```

### 2. Monitor Actively
- First 24 hours: Check every 2-4 hours
- First week: Daily checks
- Ongoing: Weekly reviews minimum

### 3. Keep Records
```bash
# Backup logs and metrics regularly
cp polymarket_agent.log logs/agent_$(date +%Y%m%d).log
cp metrics.json metrics/metrics_$(date +%Y%m%d).json
```

### 4. Have an Exit Plan
- Know how to stop the agent (Ctrl+C)
- Know how to close positions manually
- Have Polymarket UI bookmarked
- Keep emergency contacts ready

---

## 🚨 Emergency Procedures

### Stop Trading Immediately

```bash
# 1. Stop the agent
Ctrl+C

# 2. Verify it stopped
ps aux | grep polymarket_agent_v2.py

# 3. Check open positions
# Visit: https://polymarket.com/profile/YOUR_ADDRESS
```

### Close All Positions Manually

If you need to exit all positions:

1. Go to Polymarket website
2. Navigate to your profile
3. View open positions
4. Manually close each position
5. Verify closures on Polygonscan

### Recover from Issues

```bash
# 1. Review what happened
tail -200 polymarket_agent.log > incident_log.txt

# 2. Check metrics
cp metrics.json incident_metrics.json

# 3. Analyze and fix
# - Review logs for errors
# - Check configuration
# - Verify wallet state
# - Test in paper trading again
```

---

## ✅ Production Readiness Checklist

Before going live with real money:

**Testing**
- [ ] Paper trading for 24+ hours
- [ ] All unit tests passing
- [ ] No critical errors in logs
- [ ] Strategy shows promise

**Configuration**
- [ ] Conservative risk limits set
- [ ] Position sizes appropriate
- [ ] Confidence threshold reasonable
- [ ] Scan interval not too aggressive

**Wallet**
- [ ] Private key secure and backed up
- [ ] Sufficient MATIC for gas (5-10 MATIC)
- [ ] USDC balance for trading
- [ ] Wallet address verified

**Monitoring**
- [ ] Know how to check logs
- [ ] Know how to read metrics
- [ ] Can access Polymarket UI
- [ ] Can stop agent quickly

**Knowledge**
- [ ] Understand all risk parameters
- [ ] Know how to close positions
- [ ] Have emergency plan
- [ ] Understand costs (gas fees)

---

## 📞 Support Resources

### Polymarket Resources
- Website: https://polymarket.com
- Docs: https://docs.polymarket.com
- Discord: https://discord.gg/polymarket

### Polygon Resources
- Explorer: https://polygonscan.com
- Faucet (testnet): https://faucet.polygon.technology
- Status: https://status.polygon.technology

### Agent Resources
- Logs: `polymarket_agent.log`
- Metrics: `metrics.json`
- Tests: `python test_agent.py`

---

## 🎯 Summary

**Testing Progression:**

1. **Paper Trading** (1-2 weeks)
   - Zero risk
   - Validate strategy
   - Build confidence

2. **Small Production** (1 week)
   - Minimal risk ($10-25 positions)
   - Verify real execution
   - Monitor closely

3. **Full Production** (Ongoing)
   - Normal parameters
   - Regular monitoring
   - Continuous optimization

**Remember:**
- ⚠️ Start with paper trading
- ⚠️ Test thoroughly before going live
- ⚠️ Start small in production
- ⚠️ Monitor actively
- ⚠️ Only risk what you can afford to lose

---

*Good luck with your trading! Stay safe and trade responsibly.* 🚀
