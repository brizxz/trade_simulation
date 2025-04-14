#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Cryptocurrency Trading Backtest System
Strategy: Moving Average Crossover with Multiple Technical Indicators
Uses Binance API for historical data
Features:
1. 24/7 trading simulation for crypto markets
2. Additional technical indicators (RSI, MACD, Bollinger Bands)
3. Position sizing based on volatility
4. Risk management with dynamic stop-loss
5. Support for multiple trading pairs
"""

from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import logging
import sys
import time
from typing import Dict, List, Tuple, Optional

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_trading_backtest.log", mode='w', encoding='utf-8')
    ]
)

# -------------------------------
# Technical Indicator Functions
# -------------------------------
def compute_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_bollinger_bands(data: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)
    return upper_band, middle_band, lower_band

def compute_macd(data: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series]:
    """Calculate MACD and Signal line"""
    exp1 = data.ewm(span=fast_period, adjust=False).mean()
    exp2 = data.ewm(span=slow_period, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal

def compute_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period, min_periods=1).mean()

def download_crypto_data(symbol: str, interval: str, start_date: str, end_date: str, 
                        api_key: Optional[str] = None, api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Download historical cryptocurrency data from Binance
    
    Parameters:
    - symbol: Trading pair (e.g., 'BTCUSDT')
    - interval: Timeframe (e.g., '1h', '4h', '1d')
    - start_date: Start date in 'YYYY-MM-DD' format
    - end_date: End date in 'YYYY-MM-DD' format
    """
    logging.info(f"Downloading {symbol} data from Binance ({interval} interval)...")
    
    try:
        client = Client(api_key, api_secret)
        
        # Convert dates to milliseconds timestamp
        start_ts = int(datetime.datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        # Get historical klines/candlestick data
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_ts,
            end_str=end_ts
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignored'
        ])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert string values to float
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = df[col].astype(float)
            
        logging.info(f"Successfully downloaded {len(df)} candlesticks")
        return df
        
    except Exception as e:
        logging.error(f"Error downloading data: {str(e)}")
        return pd.DataFrame()

def calculate_indicators(data: pd.DataFrame, ma_short: int = 10, ma_long: int = 30) -> pd.DataFrame:
    """Calculate all technical indicators"""
    logging.info("Calculating technical indicators...")
    
    # Moving averages
    data[f'MA_{ma_short}'] = data['Close'].rolling(window=ma_short).mean()
    data[f'MA_{ma_long}'] = data['Close'].rolling(window=ma_long).mean()
    
    # RSI
    data['RSI'] = compute_rsi(data['Close'])
    
    # Bollinger Bands
    data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = compute_bollinger_bands(data['Close'])
    
    # MACD
    data['MACD'], data['MACD_Signal'] = compute_macd(data['Close'])
    
    # ATR for volatility-based position sizing
    data['ATR'] = compute_atr(data)
    
    data.dropna(inplace=True)
    return data

def generate_signals(data: pd.DataFrame, ma_short: int = 10, ma_long: int = 30,
                    rsi_oversold: int = 30, rsi_overbought: int = 70) -> pd.DataFrame:
    """
    Generate trading signals based on multiple indicators
    Returns 1 for buy, -1 for sell, 0 for hold
    """
    logging.info("Generating trading signals with multiple indicators...")
    
    data['Signal'] = 0
    
    # MA Crossover
    ma_crossover_buy = (data[f'MA_{ma_short}'] > data[f'MA_{ma_long}']) & \
                      (data[f'MA_{ma_short}'].shift(1) <= data[f'MA_{ma_long}'].shift(1))
    ma_crossover_sell = (data[f'MA_{ma_short}'] < data[f'MA_{ma_long}']) & \
                       (data[f'MA_{ma_short}'].shift(1) >= data[f'MA_{ma_long}'].shift(1))
    
    # RSI conditions
    rsi_buy = data['RSI'] < rsi_oversold
    rsi_sell = data['RSI'] > rsi_overbought
    
    # MACD crossover
    macd_buy = (data['MACD'] > data['MACD_Signal']) & \
               (data['MACD'].shift(1) <= data['MACD_Signal'].shift(1))
    macd_sell = (data['MACD'] < data['MACD_Signal']) & \
                (data['MACD'].shift(1) >= data['MACD_Signal'].shift(1))
    
    # Combine signals
    buy_signal = ma_crossover_buy & (rsi_buy | macd_buy)
    sell_signal = ma_crossover_sell | (rsi_sell & macd_sell)
    
    data.loc[buy_signal, 'Signal'] = 1
    data.loc[sell_signal, 'Signal'] = -1
    
    return data

def calculate_position_size(price: float, atr: float, risk_per_trade: float,
                          account_size: float, max_risk_pct: float = 0.02) -> float:
    """
    Calculate position size based on volatility (ATR)
    """
    max_risk_amount = account_size * max_risk_pct
    risk_amount = min(risk_per_trade, max_risk_amount)
    position_size = risk_amount / (atr * 2)  # Use 2 ATR as initial stop loss
    return position_size

def simulate_trading(data: pd.DataFrame, initial_capital: float,
                    risk_per_trade: float = 100.0, max_position_pct: float = 0.2,
                    stop_loss_atr_multiplier: float = 2.0) -> pd.DataFrame:
    """
    Simulate cryptocurrency trading with position sizing and risk management
    """
    logging.info("Simulating crypto trading...")
    
    portfolio = {
        'cash': initial_capital,
        'position': 0.0,
        'avg_price': 0.0
    }
    
    portfolio_values = []
    positions = []
    trades = []
    
    for idx, row in data.iterrows():
        price = row['Close']
        signal = row['Signal']
        atr = row['ATR']
        
        # Calculate stop loss price if in position
        stop_loss = None
        if portfolio['position'] > 0:
            stop_loss = portfolio['avg_price'] - (atr * stop_loss_atr_multiplier)
        elif portfolio['position'] < 0:
            stop_loss = portfolio['avg_price'] + (atr * stop_loss_atr_multiplier)
        
        # Check stop loss
        if stop_loss is not None:
            if (portfolio['position'] > 0 and price < stop_loss) or \
               (portfolio['position'] < 0 and price > stop_loss):
                # Stop loss hit - close position
                portfolio['cash'] += portfolio['position'] * price
                portfolio['position'] = 0.0
                portfolio['avg_price'] = 0.0
                trades.append({
                    'timestamp': idx,
                    'type': 'stop_loss',
                    'price': price,
                    'size': portfolio['position']
                })
        
        # Process signals
        if signal != 0 and portfolio['position'] == 0:
            # Calculate position size
            pos_size = calculate_position_size(
                price, atr, risk_per_trade,
                portfolio['cash'], max_position_pct
            )
            
            if signal == 1:  # Buy
                cost = pos_size * price
                if cost <= portfolio['cash']:
                    portfolio['position'] = pos_size
                    portfolio['cash'] -= cost
                    portfolio['avg_price'] = price
                    trades.append({
                        'timestamp': idx,
                        'type': 'buy',
                        'price': price,
                        'size': pos_size
                    })
            elif signal == -1:  # Sell
                portfolio['position'] = -pos_size
                portfolio['cash'] += pos_size * price
                portfolio['avg_price'] = price
                trades.append({
                    'timestamp': idx,
                    'type': 'sell',
                    'price': price,
                    'size': -pos_size
                })
        
        # Record portfolio value
        portfolio_value = portfolio['cash'] + (portfolio['position'] * price)
        portfolio_values.append(portfolio_value)
        positions.append(portfolio['position'])
    
    # Add results to DataFrame
    data['Portfolio_Value'] = portfolio_values
    data['Position'] = positions
    data['Return'] = data['Portfolio_Value'].pct_change()
    data['Strategy_Return'] = data['Return'].fillna(0)
    data['Cumulative_Strategy_Return'] = (1 + data['Strategy_Return']).cumprod()
    data['Market_Return'] = data['Close'].pct_change().fillna(0)
    data['Cumulative_Market_Return'] = (1 + data['Market_Return']).cumprod()
    
    return data, trades

def calculate_performance_metrics(data: pd.DataFrame, trades: List[Dict]) -> Dict:
    """Calculate trading performance metrics"""
    logging.info("Calculating performance metrics...")
    
    # Calculate returns and drawdown
    returns = data['Strategy_Return']
    cum_returns = data['Cumulative_Strategy_Return']
    running_max = cum_returns.cummax()
    drawdown = (cum_returns - running_max) / running_max
    
    # Calculate trade statistics
    profitable_trades = len([t for t in trades if 
        (t['type'] == 'buy' and t['price'] < data.loc[t['timestamp']:].iloc[1]['Close']) or
        (t['type'] == 'sell' and t['price'] > data.loc[t['timestamp']:].iloc[1]['Close'])
    ])
    total_trades = len(trades)
    
    metrics = {
        'total_return': (cum_returns.iloc[-1] - 1) * 100,
        'annual_return': ((cum_returns.iloc[-1]) ** (252/len(data)) - 1) * 100,
        'max_drawdown': drawdown.min() * 100,
        'sharpe_ratio': np.sqrt(252) * returns.mean() / returns.std(),
        'win_rate': (profitable_trades / total_trades * 100) if total_trades > 0 else 0,
        'total_trades': total_trades
    }
    
    logging.info("Performance Metrics:")
    for key, value in metrics.items():
        logging.info(f"{key}: {value:.2f}")
    
    return metrics

def plot_results(data: pd.DataFrame, symbol: str, trades: List[Dict]):
    """Plot trading results with entry/exit points"""
    plt.style.use('seaborn')
    fig, axs = plt.subplots(3, 1, figsize=(15, 20), gridspec_kw={'height_ratios': [3, 2, 2]})
    
    # Plot 1: Price and Indicators
    axs[0].plot(data.index, data['Close'], label='Price', alpha=0.7)
    axs[0].plot(data.index, data['MA_10'], label='MA(10)', alpha=0.6)
    axs[0].plot(data.index, data['MA_30'], label='MA(30)', alpha=0.6)
    axs[0].plot(data.index, data['BB_Upper'], '--', label='BB Upper', alpha=0.3)
    axs[0].plot(data.index, data['BB_Lower'], '--', label='BB Lower', alpha=0.3)
    
    # Plot trades
    for trade in trades:
        if trade['type'] == 'buy':
            axs[0].scatter(trade['timestamp'], trade['price'], 
                          marker='^', color='green', s=100)
        elif trade['type'] == 'sell':
            axs[0].scatter(trade['timestamp'], trade['price'], 
                          marker='v', color='red', s=100)
        elif trade['type'] == 'stop_loss':
            axs[0].scatter(trade['timestamp'], trade['price'], 
                          marker='x', color='black', s=100)
    
    axs[0].set_title(f'{symbol} Price Action and Trades')
    axs[0].set_ylabel('Price')
    axs[0].legend()
    
    # Plot 2: Strategy vs Market Returns
    axs[1].plot(data.index, data['Cumulative_Strategy_Return'], 
                label='Strategy', color='blue')
    axs[1].plot(data.index, data['Cumulative_Market_Return'], 
                label='Buy & Hold', color='gray', alpha=0.5)
    axs[1].set_title('Cumulative Returns: Strategy vs Market')
    axs[1].set_ylabel('Cumulative Return')
    axs[1].legend()
    
    # Plot 3: Portfolio Value
    axs[2].plot(data.index, data['Portfolio_Value'], label='Portfolio Value', 
                color='green')
    axs[2].set_title('Portfolio Value Evolution')
    axs[2].set_ylabel('Portfolio Value')
    axs[2].legend()
    
    plt.tight_layout()
    plt.show()

def main():
    # Configuration
    symbol = 'BTCUSDT'
    start_date = '2024-01-01'
    end_date = '2024-04-01'
    interval = '1h'
    initial_capital = 10000.0
    risk_per_trade = 100.0
    
    # Your Binance API credentials (optional for historical data)
    api_key = None
    api_secret = None
    
    # Download data
    data = download_crypto_data(symbol, interval, start_date, end_date, api_key, api_secret)
    if data.empty:
        logging.error("Failed to download data. Exiting...")
        return None
    
    # Calculate indicators and generate signals
    data = calculate_indicators(data)
    data = generate_signals(data)
    
    # Simulate trading
    data, trades = simulate_trading(data, initial_capital, risk_per_trade)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(data, trades)
    
    # Plot results
    plot_results(data, symbol, trades)
    
    return metrics, data, trades

if __name__ == '__main__':
    results = main()
    if results:
        metrics, data, trades = results
        logging.info("Backtest completed successfully")
    else:
        logging.error("Backtest failed to complete") 