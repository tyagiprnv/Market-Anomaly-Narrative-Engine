#!/usr/bin/env python
"""Debug script to understand why BTC/ETH drops aren't being detected."""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

engine = create_engine('postgresql://mane_pranav:mane_pranav_pass@localhost:5433/mane_db')

def analyze_symbol(symbol: str, hours_back: int = 4):
    """Analyze detection logic for a symbol."""
    print(f"\n{'='*60}")
    print(f"ANALYSIS: {symbol}")
    print(f"{'='*60}")

    cutoff = datetime.now() - timedelta(hours=hours_back)

    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT timestamp, price, volume_24h as volume
            FROM prices
            WHERE symbol = :symbol AND timestamp >= :cutoff
            ORDER BY timestamp
        '''), {'symbol': symbol, 'cutoff': cutoff})

        data = result.fetchall()
        df = pd.DataFrame(data, columns=['timestamp', 'price', 'volume'])

    if len(df) < 60:
        print(f"Not enough data: {len(df)} points")
        return

    print(f"Loaded {len(df)} price points")
    print(f"First: {df['timestamp'].iloc[0]}")
    print(f"Last: {df['timestamp'].iloc[-1]}")
    print(f"Price: ${df['price'].iloc[0]:.2f} → ${df['price'].iloc[-1]:.2f}")
    total_change = ((df['price'].iloc[-1] - df['price'].iloc[0]) / df['price'].iloc[0]) * 100
    print(f"Total change: {total_change:+.2f}%")

    # Test multi-timeframe windows
    windows = [5, 15, 30, 60]
    baseline_multiplier = 3

    print(f"\n--- Multi-Timeframe Analysis ---")
    for window_minutes in windows:
        if len(df) < window_minutes * baseline_multiplier:
            print(f"\n{window_minutes}-minute window: Not enough data")
            continue

        # Cumulative return for current window
        price_start = df['price'].iloc[-window_minutes]
        price_end = df['price'].iloc[-1]
        cumulative_return = ((price_end - price_start) / price_start) * 100

        # Baseline window (excluding current window)
        baseline_window_size = window_minutes * baseline_multiplier
        baseline_start_idx = max(0, len(df) - baseline_window_size)
        baseline_end_idx = len(df) - window_minutes

        baseline_df = df.iloc[baseline_start_idx:baseline_end_idx]

        # Calculate baseline rolling returns
        baseline_returns = []
        for i in range(len(baseline_df) - window_minutes + 1):
            if i + window_minutes >= len(baseline_df):
                break
            start_p = baseline_df['price'].iloc[i]
            end_p = baseline_df['price'].iloc[i + window_minutes]
            ret = ((end_p - start_p) / start_p) * 100
            baseline_returns.append(ret)

        if not baseline_returns:
            print(f"\n{window_minutes}-minute window: No baseline returns")
            continue

        baseline_mean = np.mean(baseline_returns)
        baseline_std = np.std(baseline_returns)

        if baseline_std == 0:
            z_score = 0
        else:
            z_score = (cumulative_return - baseline_mean) / baseline_std

        print(f"\n{window_minutes}-minute window:")
        print(f"  Cumulative return: {cumulative_return:+.2f}%")
        print(f"  Baseline mean: {baseline_mean:+.4f}%")
        print(f"  Baseline std: {baseline_std:.4f}%")
        print(f"  Z-score: {z_score:+.2f}")
        print(f"  Passes min_return (1.5%)? {abs(cumulative_return) >= 1.5}")
        print(f"  Passes Z-threshold (3.5)? {abs(z_score) >= 3.5}")
        print(f"  → Would detect? {abs(cumulative_return) >= 1.5 and abs(z_score) >= 3.5}")

if __name__ == "__main__":
    analyze_symbol("BTC-USD", hours_back=4)
    analyze_symbol("ETH-USD", hours_back=4)
