#!/usr/bin/env python3
"""Create a synthetic anomaly in the last hour to trigger detection."""

import asyncio
from datetime import datetime, timedelta, UTC

from config.settings import Settings
from src.database.connection import get_db_context, init_database
from src.database.models import Price
from rich.console import Console

console = Console()


async def main():
    """Create synthetic recent anomaly."""
    settings = Settings()
    init_database(settings.database.url)

    console.print("[cyan]Creating synthetic anomaly in the last hour...[/cyan]")

    now = datetime.now(UTC)
    start_time = now - timedelta(minutes=90)

    timestamps = []
    prices = []
    volumes = []

    # 60 minutes of baseline at ~$91,000
    for i in range(60):
        timestamps.append(start_time + timedelta(minutes=i))
        prices.append(91000 + (i % 10 - 5) * 50)
        volumes.append(1_000_000_000)

    # 30 minutes of surge to $95,500 (+4.9%, Z-score > 3)
    surge_prices = [91500, 92000, 92500, 93000, 93400, 93800, 94200, 94600, 94900, 95200,
                    95300, 95400, 95500, 95400, 95500, 95600, 95500, 95400, 95300, 95200,
                    95100, 95000, 94900, 94800, 94700, 94800, 94900, 95000, 95100, 95200]

    for i in range(30):
        timestamps.append(start_time + timedelta(minutes=60 + i))
        prices.append(surge_prices[i])
        volumes.append(1_500_000_000)  # Higher volume

    # Insert
    with get_db_context() as session:
        # Delete existing demo data
        session.query(Price).filter(Price.source == "test_demo").delete()

        price_records = []
        for ts, price, volume in zip(timestamps, prices, volumes):
            price_records.append(
                Price(
                    symbol="BTC-USD",
                    timestamp=ts,
                    price=price,
                    volume_24h=volume,
                    source="test_demo",
                )
            )

        session.bulk_save_objects(price_records)
        session.commit()

    console.print(f"[green]✓ Created {len(price_records)} price records[/green]")
    console.print(f"[green]  Time range: {start_time} to {now}[/green]")
    console.print(f"[green]  Baseline: ~$91,000[/green]")
    console.print(f"[green]  Peak: $95,500 (+4.9%)[/green]")
    console.print("\n[yellow]Now run: mane detect --symbol BTC-USD --news-mode live[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
