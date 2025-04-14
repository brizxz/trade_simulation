# Intraday Trading Backtest System

A flexible and extensible backtesting framework for intraday trading strategies with multiple strategy options and comprehensive performance analysis.

## Features

- **Multiple Trading Strategies**: MA Crossover, RSI Reversal, and Price Breakout
- **Customizable Parameters**: Fine-tune each strategy through command line arguments
- **Cash Account Simulation**: Realistic tracking of cash, positions and average cost
- **Stop Loss Protection**: Protect your capital with customizable stop loss limits
- **Performance Metrics**: Comprehensive analysis including Sharpe ratio, drawdown, and returns
- **Visualization**: Detailed charts with price action, indicators, signals, and performance

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/trading-backtest.git
cd trading-backtest
```

2. Install required packages:
```bash
pip install pandas numpy matplotlib alpha_vantage
```

3. Get an Alpha Vantage API key (free tier available at https://www.alphavantage.co/support/#api-key)

## Usage

The system supports running backtests from the command line with various parameters:

```bash
python trade.py \
  --symbol AAPL \
  --start_date 2025-03-13 \
  --end_date 2025-04-11 \
  --strategy ma_crossover \
  --initial_capital 10000
```

### Required Parameters

| Parameter | Description |
|-----------|-------------|
| `--symbol` | Stock symbol (e.g., AAPL, MSFT, INTC) |
| `--start_date` | Start date in YYYY-MM-DD format |
| `--end_date` | End date in YYYY-MM-DD format |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--interval` | 5min | Trading interval (1min, 5min, 15min, 30min, 60min) |
| `--initial_capital` | 10000.0 | Initial capital in USD |
| `--api_key` | CPSVFU8571VH65E3 | Alpha Vantage API key |
| `--strategy` | ma_crossover | Trading strategy to use (ma_crossover, rsi_reversal, breakout) |

### Strategy-Specific Parameters

#### MA Crossover Strategy
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ma_short` | 10 | Short moving average period |
| `--ma_long` | 30 | Long moving average period |
| `--adx_threshold` | 25.0 | ADX threshold for trend strength |

#### RSI Reversal Strategy
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rsi_period` | 14 | Period for RSI calculation |
| `--rsi_oversold` | 30 | RSI oversold threshold |
| `--rsi_overbought` | 70 | RSI overbought threshold |

#### Breakout Strategy
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--breakout_period` | 20 | Lookback period for breakout strategy |
| `--breakout_threshold` | 0.02 | Breakout threshold as percentage (0.02 = 2%) |

### Trading Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--trade_unit` | 2 | Base trade unit size |
| `--max_units` | 10 | Maximum position size in units |
| `--stop_loss_pct` | 0.03 | Stop loss percentage (0.03 = 3%) |
| `--cost_factor` | 0.001 | Transaction cost factor (0.001 = 0.1%) |
| `--cooldown_period` | 1 | Cooldown period after a trade in bars |

## Trading Strategies

### 1. Moving Average Crossover (ma_crossover)
Uses crossovers between short and long-term moving averages to generate trading signals. Buys when the short MA crosses above the long MA and sells when it crosses below. The ADX indicator is used as a filter to ensure strong trends.

Example:
```bash
python trade.py --symbol AAPL --start_date 2025-03-13 --end_date 2025-04-11 --strategy ma_crossover --ma_short 8 --ma_long 21
```

### 2. RSI Reversal (rsi_reversal)
Uses the Relative Strength Index (RSI) to identify oversold and overbought conditions. Buys when the RSI crosses above the oversold threshold and sells when it crosses below the overbought threshold.

Example:
```bash
python trade.py --symbol MSFT --start_date 2025-03-13 --end_date 2025-04-11 --strategy rsi_reversal --rsi_oversold 25 --rsi_overbought 75
```

### 3. Price Breakout (breakout)
Identifies price breakouts from recent high and low levels. Buys when price breaks above the highest price in the lookback period and sells when it breaks below the lowest price.

Example:
```bash
python trade.py --symbol INTC --start_date 2025-03-13 --end_date 2025-04-11 --strategy breakout --breakout_period 15 --breakout_threshold 0.015
```

## Output

The system generates:

1. **Log File** (`trading_backtest.log`): Detailed information about the backtest process
2. **Performance Metrics**:
   - Total return
   - Max drawdown
   - Sharpe ratio
   - Daily return statistics
3. **Portfolio Summary**:
   - Initial and final capital
   - Final positions and cash
   - Return percentages
4. **Charts**:
   - Price action with strategy-specific indicators
   - Buy/sell signals
   - Cumulative returns comparison (strategy vs market)
   - Portfolio value evolution

The chart is saved as `{symbol}_{strategy}_backtest_results.png` in the current directory.

## Limitations

- The Alpha Vantage free tier has rate limits (5 API calls per minute) and limited data
- Backtesting results are not indicative of future performance
- Transaction costs are simplified
- No slippage or liquidity considerations

## License

This project is licensed under the MIT License - see the LICENSE file for details. 