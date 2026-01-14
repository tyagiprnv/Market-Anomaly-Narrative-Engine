"""Example script to test data ingestion clients.

This script demonstrates how to use the Coinbase and Binance clients
to fetch real-time cryptocurrency price data.

Usage:
    python examples/test_data_ingestion.py
"""

import asyncio
from src.phase1_detector.data_ingestion import CoinbaseClient, BinanceClient


async def test_coinbase():
    """Test Coinbase client."""
    print("=" * 60)
    print("Testing Coinbase Client")
    print("=" * 60)

    async with CoinbaseClient() as client:
        # Health check
        is_healthy = await client.health_check()
        print(f"Coinbase API Health: {'✓ OK' if is_healthy else '✗ Failed'}\n")

        if not is_healthy:
            print("Coinbase API is not accessible. Skipping tests.\n")
            return

        # Fetch single price
        print("Fetching BTC-USD price...")
        try:
            btc_price = await client.get_price("BTC-USD")
            print(f"  Symbol: {btc_price.symbol}")
            print(f"  Price: ${btc_price.price:,.2f}")
            print(f"  24h Volume: ${btc_price.volume_24h:,.0f}")
            print(f"  24h High: ${btc_price.high_24h:,.2f}")
            print(f"  24h Low: ${btc_price.low_24h:,.2f}")
            print(f"  Bid: ${btc_price.bid:,.2f}")
            print(f"  Ask: ${btc_price.ask:,.2f}")
            print(f"  Source: {btc_price.source}")
            print(f"  Timestamp: {btc_price.timestamp}\n")
        except Exception as e:
            print(f"  Error: {e}\n")

        # Fetch multiple prices
        print("Fetching multiple symbols...")
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
        try:
            prices = await client.get_prices(symbols)
            print(f"  Successfully fetched {len(prices)} symbols:\n")
            for price in prices:
                print(f"  {price.symbol:10} ${price.price:10,.2f}")
        except Exception as e:
            print(f"  Error: {e}")

    print()


async def test_binance():
    """Test Binance client."""
    print("=" * 60)
    print("Testing Binance Client")
    print("=" * 60)

    async with BinanceClient() as client:
        # Health check
        is_healthy = await client.health_check()
        print(f"Binance API Health: {'✓ OK' if is_healthy else '✗ Failed'}\n")

        if not is_healthy:
            print("Binance API is not accessible. Skipping tests.\n")
            return

        # Fetch single price
        print("Fetching BTC-USD price...")
        try:
            btc_price = await client.get_price("BTC-USD")
            print(f"  Symbol: {btc_price.symbol}")
            print(f"  Price: ${btc_price.price:,.2f}")
            print(f"  24h Volume: ${btc_price.volume_24h:,.0f}")
            print(f"  24h High: ${btc_price.high_24h:,.2f}")
            print(f"  24h Low: ${btc_price.low_24h:,.2f}")
            print(f"  Bid: ${btc_price.bid:,.2f}")
            print(f"  Ask: ${btc_price.ask:,.2f}")
            print(f"  Source: {btc_price.source}")
            print(f"  Timestamp: {btc_price.timestamp}\n")
        except Exception as e:
            print(f"  Error: {e}\n")

        # Fetch multiple prices
        print("Fetching multiple symbols...")
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
        try:
            prices = await client.get_prices(symbols)
            print(f"  Successfully fetched {len(prices)} symbols:\n")
            for price in prices:
                print(f"  {price.symbol:10} ${price.price:10,.2f}")
        except Exception as e:
            print(f"  Error: {e}")

    print()


async def main():
    """Run all tests."""
    print("\nMarket Anomaly Narrative Engine - Data Ingestion Test\n")

    # Test both clients
    await test_coinbase()
    await test_binance()

    print("=" * 60)
    print("✓ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
