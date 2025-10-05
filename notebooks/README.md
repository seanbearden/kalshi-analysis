# Kalshi Analysis Notebooks

Professional-grade data science workflows for market data exploration, strategy backtesting, and performance optimization.

## Quick Start

```bash
# Install dependencies
cd notebooks
pip install -r requirements.txt

# Start Jupyter
jupyter notebook
```

## Structure

### Utils Framework (Reusable Modules)
```
utils/
├── __init__.py          # Module exports
├── database.py          # Database connection & data loading
├── backtesting.py       # Strategy framework & backtest engine
├── metrics.py           # Performance calculations (Sharpe, Sortino, drawdown)
└── visualization.py     # Plotting utilities & reliability diagrams
```

### Notebooks (Execution Order)

#### 01_data_exploration.ipynb
**Purpose**: Understand collected market data

Features:
- Database connectivity validation
- Price distribution analysis
- Time series visualization
- Volume analysis by ticker
- Data quality checks

**Run this first** to validate data collection.

#### 02_strategy_backtest.ipynb
**Purpose**: Implement and test trading strategies

Features:
- Mean reversion strategy implementation
- Backtest engine with P&L tracking
- Performance metrics (Sharpe, Sortino, drawdown, win rate)
- Equity curve and returns visualization

**Phase 1C Requirement**: Sharpe ratio > 0.5

#### 03_calibration_analysis.ipynb ⭐ **NEW**
**Purpose**: Validate market prediction quality

Features:
- Reliability diagram (predicted vs actual outcomes)
- Calibration metrics (MSE, Brier score)
- Time-based calibration analysis
- Market efficiency assessment

**CRITICAL for Phase 1C**: Demonstrates prediction quality.

#### 04_strategy_optimization.ipynb ⭐ **NEW**
**Purpose**: Systematic parameter tuning

Features:
- Grid search over parameter space
- Sharpe ratio optimization
- Parameter sensitivity analysis
- Heatmaps and visualizations
- Best parameter identification

**Goal**: Maximize Sharpe ratio to meet Phase 1C criteria.

## Usage Workflow

### Step 1: Data Collection
Ensure poller is running and collecting data:
```bash
docker compose --profile poller up -d
docker compose logs -f poller
```

**Minimum data requirements**:
- 30+ minutes for basic backtesting
- 2+ hours for reliable optimization
- Resolved markets for calibration analysis

### Step 2: Run Notebooks in Order

```bash
cd notebooks
jupyter notebook
```

**Execution sequence**:
1. `01_data_exploration.ipynb` - Validate data quality
2. `02_strategy_backtest.ipynb` - Test mean reversion strategy
3. `04_strategy_optimization.ipynb` - Optimize parameters for Sharpe >0.5
4. `03_calibration_analysis.ipynb` - Validate prediction quality (requires resolved markets)

## Key Features

### Backtesting Framework
- **Strategy Base Class**: Abstract class for custom strategies
- **MeanReversionStrategy**: Concrete implementation with tunable parameters
- **Backtest Engine**: Position management, P&L tracking, multi-ticker support
- **Performance Metrics**: Sharpe, Sortino, Calmar, drawdown, profit factor

### Visualization Suite
- Equity curves and cumulative returns
- Drawdown analysis
- P&L distribution histograms
- **Reliability diagrams** (calibration quality)
- Strategy summary dashboards (6-panel view)

### Parameter Optimization
- Grid search over parameter combinations
- Sensitivity analysis (window, threshold, position size)
- Heatmaps for parameter interactions
- Automatic best-parameter selection

## Strategy Implementation

### Mean Reversion Strategy
**Logic**:
- Calculate rolling mean and standard deviation (configurable window)
- Buy signal: price < mean - (threshold × std)
- Sell signal: price > mean + (threshold × std)
- Exit: price returns to neutral (0.50) or opposite signal

**Tunable Parameters**:
- `window`: Rolling window size (10-30 snapshots)
- `std_threshold`: Standard deviation multiplier (1.0-2.5)
- `position_size`: Fraction of capital per trade (0.05-0.15)

### Custom Strategy Development
```python
from utils import Strategy, Backtest

class MyStrategy(Strategy):
    def generate_signals(self, df):
        # Your logic here
        df['signal'] = ...  # 1=buy, -1=sell, 0=hold
        return df

strategy = MyStrategy()
backtest = Backtest(strategy, initial_capital=10000)
result = backtest.run(df)
```

## Phase 1C Success Criteria

**Requirements**:
- ✅ Jupyter notebook environment
- ✅ Backtesting framework
- ✅ Performance metrics calculator
- ✅ Calibration analysis
- ⏳ **Strategy with Sharpe ratio > 0.5** (depends on data)

**If Sharpe < 0.5**:
1. Collect more data (let poller run longer)
2. Use `04_strategy_optimization.ipynb` for parameter tuning
3. Try alternative strategies (momentum, arbitrage)
4. Focus on specific market types
5. Implement advanced risk management

**If Sharpe > 0.5**:
✅ **Phase 1C COMPLETE!**

Proceed to Phase 2 (WebSocket real-time monitoring).

## Database Connection

Notebooks connect to PostgreSQL via `utils.get_engine()`:
- Host: `localhost`
- Port: `5432`
- Database: `kalshi`
- User: `kalshi`
- Password: `kalshi`  <!-- pragma: allowlist secret -->

Ensure Docker Compose port forwarding is active.

## Advanced Usage

### Load Specific Market Data
```python
from utils import get_engine, load_market_data

engine = get_engine()
df = load_market_data(
    engine,
    ticker='SPECIFIC_TICKER',
    start_time=datetime(2025, 1, 1),
    min_snapshots=50
)
```

### Run Multi-Ticker Backtest
```python
from utils import MeanReversionStrategy, run_multi_ticker_backtest

strategy = MeanReversionStrategy(window=20, std_threshold=1.5)
result = run_multi_ticker_backtest(df, strategy, initial_capital=10000)
```

### Calculate Performance Metrics
```python
from utils import PerformanceMetrics

metrics = PerformanceMetrics.calculate_all(result)
PerformanceMetrics.print_metrics(metrics)
```

### Create Reliability Diagram
```python
from utils.visualization import plot_reliability_diagram

fig = plot_reliability_diagram(
    predicted_probs=predictions,
    actual_outcomes=outcomes,
    n_bins=10
)
```

## Next Steps

**After Phase 1C completion**:
1. Review calibration quality (03_calibration_analysis.ipynb)
2. Document optimal parameters (from 04_strategy_optimization.ipynb)
3. Prepare for Phase 2 WebSocket integration
4. Design live strategy monitoring dashboard

See `docs/phase-2-architecture.md` for Phase 2 planning.
