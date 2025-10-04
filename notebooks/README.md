# Kalshi Analysis Notebooks

Jupyter notebooks for market data exploration and strategy backtesting.

## Prerequisites

```bash
pip install pandas numpy matplotlib seaborn scipy sqlalchemy psycopg2-binary jupyter
```

## Notebooks

### 01_data_exploration.ipynb

Exploratory data analysis of Kalshi market snapshots:
- Database connectivity
- Price distribution analysis
- Time series visualization
- Volume analysis
- Data quality checks

**Run this first** to understand the collected data.

### 02_strategy_backtest.ipynb

Trading strategy implementation and backtesting:
- Mean reversion strategy
- Backtest engine with P&L tracking
- Performance metrics (Sharpe ratio, drawdown, win rate)
- Visualization of equity curve and returns

**Phase 1 Success Criteria**: Sharpe ratio > 0.5

## Usage

1. **Ensure poller is running** and collecting data:
   ```bash
   docker compose --profile poller up -d
   docker compose logs -f poller
   ```

2. **Wait for data collection** (at least 30+ minutes for meaningful backtests)

3. **Start Jupyter**:
   ```bash
   cd notebooks
   jupyter notebook
   ```

4. **Run notebooks** in order:
   - Start with `01_data_exploration.ipynb`
   - Proceed to `02_strategy_backtest.ipynb`

## Strategy Notes

The mean reversion strategy:
- Calculates rolling mean and standard deviation (20-snapshot window)
- Buys when price < mean - 1.5σ (undervalued)
- Sells when price > mean + 1.5σ (overvalued)
- Exits at neutral (0.50 probability)

### If Sharpe < 0.5

Try optimizing:
1. **Parameters**: window size, std threshold, position size
2. **Alternative strategies**: momentum, arbitrage, volume-based
3. **Risk management**: stop-loss, volatility sizing
4. **Data filtering**: focus on liquid markets with price movement

### If Sharpe > 0.5

**Phase 1 Complete!** ✅

Proceed to Phase 2 (WebSocket real-time monitoring) per `docs/phase-2-architecture.md`.

## Database Connection

Notebooks connect to PostgreSQL:
- Host: `localhost`
- Port: `5432`
- Database: `kalshi`
- User: `kalshi`
- Password: `kalshi`  <!-- pragma: allowlist secret -->

Ensure port forwarding is active in `docker-compose.yml`.
