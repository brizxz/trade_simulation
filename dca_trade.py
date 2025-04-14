#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ladder-based Dollar Cost Averaging (DCA) Trading Strategy
Features:
1. Buy more when price drops (5% -> 10%, 10% -> 20%, etc.)
2. Take profit when price rises (10% -> 10%, 20% -> 20%, etc.)
3. Command line argument support
4. Detailed performance tracking
"""

from binance.client import Client
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import logging
import sys
import time
import argparse
from typing import Dict, List, Tuple, Optional

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("dca_trading_backtest.log", mode='w', encoding='utf-8')
    ]
)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Ladder-based DCA Trading Strategy')
    
    # Required arguments
    parser.add_argument('--symbol', type=str, required=True,
                      help='Trading pair (e.g., BTCUSDT)')
    parser.add_argument('--start_date', type=str, required=True,
                      help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=str, required=True,
                      help='End date in YYYY-MM-DD format')
    
    # Optional arguments with defaults
    parser.add_argument('--interval', type=str, default='1h',
                      help='Trading interval (1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--initial_capital', type=float, default=10000.0,
                      help='Initial capital in USDT')
    parser.add_argument('--api_key', type=str, default=None,
                      help='Binance API key')
    parser.add_argument('--api_secret', type=str, default=None,
                      help='Binance API secret')
    
    # Strategy specific parameters
    parser.add_argument('--drop_ladder', type=str, default='5,10,15,20',
                      help='Comma-separated price drop percentages for buying')
    parser.add_argument('--buy_ladder', type=str, default='10,20,30,40',
                      help='Comma-separated portfolio percentages for buying')
    parser.add_argument('--profit_ladder', type=str, default='10,20,30,40',
                      help='Comma-separated price increase percentages for selling')
    parser.add_argument('--sell_ladder', type=str, default='10,20,30,40',
                      help='Comma-separated portfolio percentages for selling')
    
    return parser.parse_args()

def download_crypto_data(symbol: str, interval: str, start_date: str, end_date: str, 
                        api_key: Optional[str] = None, api_secret: Optional[str] = None) -> pd.DataFrame:
    """Download historical cryptocurrency data from Binance"""
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

def calculate_price_changes(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate price changes from the peak and trough"""
    data['Peak_Price'] = data['Close'].rolling(window=20, min_periods=1).max()
    data['Trough_Price'] = data['Close'].rolling(window=20, min_periods=1).min()
    
    # Calculate percentage drops and increases
    data['Drop_Pct'] = ((data['Peak_Price'] - data['Close']) / data['Peak_Price']) * 100
    data['Increase_Pct'] = ((data['Close'] - data['Trough_Price']) / data['Trough_Price']) * 100
    
    return data

def generate_dca_signals(data: pd.DataFrame, drop_ladder: List[float], 
                        profit_ladder: List[float]) -> pd.DataFrame:
    """Generate trading signals based on price drops and increases"""
    data['Buy_Signal'] = 0
    data['Sell_Signal'] = 0
    
    # Generate buy signals for each drop level
    for drop_pct in drop_ladder:
        data.loc[data['Drop_Pct'] >= drop_pct, 'Buy_Signal'] = drop_pct
        
    # Generate sell signals for each profit level
    for profit_pct in profit_ladder:
        data.loc[data['Increase_Pct'] >= profit_pct, 'Sell_Signal'] = profit_pct
    
    return data

def get_ladder_percentage(signal: float, ladder_signals: List[float], 
                         ladder_percentages: List[float]) -> float:
    """Get the corresponding percentage from the ladder based on the signal"""
    if signal == 0:
        return 0
    
    for sig, pct in zip(ladder_signals, ladder_percentages):
        if signal >= sig:
            return pct
    return 0

def simulate_dca_trading(data: pd.DataFrame, initial_capital: float,
                        drop_ladder: List[float], buy_ladder: List[float],
                        profit_ladder: List[float], sell_ladder: List[float]) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Simulate ladder-based DCA trading strategy
    """
    logging.info("Simulating DCA trading strategy...")
    
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
        buy_signal = row['Buy_Signal']
        sell_signal = row['Sell_Signal']
        
        # Calculate buy amount based on drop percentage
        if buy_signal > 0:
            buy_pct = get_ladder_percentage(buy_signal, drop_ladder, buy_ladder) / 100
            buy_amount = portfolio['cash'] * buy_pct
            
            if buy_amount > 0 and portfolio['cash'] >= buy_amount:
                shares_to_buy = buy_amount / price
                portfolio['position'] += shares_to_buy
                portfolio['cash'] -= buy_amount
                
                # Update average price
                total_value = (portfolio['avg_price'] * (portfolio['position'] - shares_to_buy) + 
                             price * shares_to_buy)
                portfolio['avg_price'] = total_value / portfolio['position']
                
                trades.append({
                    'timestamp': idx,
                    'type': 'buy',
                    'price': price,
                    'amount': buy_amount,
                    'shares': shares_to_buy,
                    'trigger': f"{buy_signal:.1f}% drop"
                })
        
        # Calculate sell amount based on profit percentage
        elif sell_signal > 0 and portfolio['position'] > 0:
            sell_pct = get_ladder_percentage(sell_signal, profit_ladder, sell_ladder) / 100
            shares_to_sell = portfolio['position'] * sell_pct
            
            if shares_to_sell > 0:
                sell_amount = shares_to_sell * price
                portfolio['position'] -= shares_to_sell
                portfolio['cash'] += sell_amount
                
                trades.append({
                    'timestamp': idx,
                    'type': 'sell',
                    'price': price,
                    'amount': sell_amount,
                    'shares': shares_to_sell,
                    'trigger': f"{sell_signal:.1f}% gain"
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
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    metrics = {
        'total_return': (cum_returns.iloc[-1] - 1) * 100,
        'annual_return': ((cum_returns.iloc[-1]) ** (252/len(data)) - 1) * 100,
        'max_drawdown': drawdown.min() * 100,
        'sharpe_ratio': np.sqrt(252) * returns.mean() / returns.std(),
        'total_trades': len(trades),
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'avg_position_size': data['Position'].mean(),
        'max_position_size': data['Position'].max()
    }
    
    logging.info("Performance Metrics:")
    for key, value in metrics.items():
        logging.info(f"{key}: {value:.2f}")
    
    return metrics

def plot_results(data: pd.DataFrame, symbol: str, trades: List[Dict]):
    """Plot trading results with entry/exit points"""
    plt.style.use('seaborn')
    fig, axs = plt.subplots(4, 1, figsize=(15, 25), gridspec_kw={'height_ratios': [3, 1.5, 1.5, 1.5]})
    
    # Plot 1: Price and Trades
    axs[0].plot(data.index, data['Close'], label='Price', alpha=0.7)
    
    # Plot trades
    for trade in trades:
        if trade['type'] == 'buy':
            axs[0].scatter(trade['timestamp'], trade['price'], 
                          marker='^', color='green', s=100)
        else:  # sell
            axs[0].scatter(trade['timestamp'], trade['price'], 
                          marker='v', color='red', s=100)
    
    axs[0].set_title(f'{symbol} Price Action and Trades')
    axs[0].set_ylabel('Price')
    axs[0].legend()
    
    # Plot 2: Price Drops and Increases
    axs[1].plot(data.index, data['Drop_Pct'], label='Price Drop %', color='red', alpha=0.7)
    axs[1].plot(data.index, data['Increase_Pct'], label='Price Increase %', color='green', alpha=0.7)
    axs[1].set_title('Price Changes (%)')
    axs[1].set_ylabel('Percentage')
    axs[1].legend()
    
    # Plot 3: Strategy vs Market Returns
    axs[2].plot(data.index, data['Cumulative_Strategy_Return'], 
                label='Strategy', color='blue')
    axs[2].plot(data.index, data['Cumulative_Market_Return'], 
                label='Buy & Hold', color='gray', alpha=0.5)
    axs[2].set_title('Cumulative Returns: Strategy vs Market')
    axs[2].set_ylabel('Cumulative Return')
    axs[2].legend()
    
    # Plot 4: Portfolio Value and Position Size
    ax4_twin = axs[3].twinx()
    axs[3].plot(data.index, data['Portfolio_Value'], 
                label='Portfolio Value', color='green')
    ax4_twin.plot(data.index, data['Position'], 
                  label='Position Size', color='blue', alpha=0.5)
    axs[3].set_title('Portfolio Value and Position Size')
    axs[3].set_ylabel('Portfolio Value')
    ax4_twin.set_ylabel('Position Size')
    
    # Combine legends
    lines1, labels1 = axs[3].get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4_twin.legend(lines1 + lines2, labels1 + labels2)
    
    plt.tight_layout()
    plt.show()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Convert ladder strings to lists of floats
    drop_ladder = [float(x) for x in args.drop_ladder.split(',')]
    buy_ladder = [float(x) for x in args.buy_ladder.split(',')]
    profit_ladder = [float(x) for x in args.profit_ladder.split(',')]
    sell_ladder = [float(x) for x in args.sell_ladder.split(',')]
    
    # Sort ladders in ascending order
    drop_ladder.sort()
    buy_ladder.sort()
    profit_ladder.sort()
    sell_ladder.sort()
    
    # Download data
    data = download_crypto_data(
        args.symbol, args.interval, args.start_date, args.end_date,
        args.api_key, args.api_secret
    )
    
    if data.empty:
        logging.error("Failed to download data. Exiting...")
        return None
    
    # Calculate price changes and generate signals
    data = calculate_price_changes(data)
    data = generate_dca_signals(data, drop_ladder, profit_ladder)
    
    # Simulate trading
    data, trades = simulate_dca_trading(
        data, args.initial_capital,
        drop_ladder, buy_ladder,
        profit_ladder, sell_ladder
    )
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(data, trades)
    
    # Plot results
    plot_results(data, args.symbol, trades)
    
    return metrics, data, trades

if __name__ == '__main__':
    results = main()
    if results:
        metrics, data, trades = results
        logging.info("Backtest completed successfully")
        
        # Print detailed trade log
        logging.info("\nDetailed Trade Log:")
        for trade in trades:
            logging.info(
                f"Time: {trade['timestamp']}, Type: {trade['type'].upper()}, "
                f"Price: {trade['price']:.2f}, Amount: {trade['amount']:.2f}, "
                f"Shares: {trade['shares']:.4f}, Trigger: {trade['trigger']}"
            )
    else:
        logging.error("Backtest failed to complete") 