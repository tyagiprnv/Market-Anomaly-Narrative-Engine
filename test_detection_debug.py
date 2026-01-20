#!/usr/bin/env python3
"""Debug detection to see why anomaly isn't being found."""

import asyncio
import pandas as pd
from datetime import datetime, timedelta, UTC

from config.settings import Settings
from src.database.connection import get_db_context, init_database
from src.database.models import Price
from src.phase1_detector.anomaly_detection.statistical import AnomalyDetector
from rich.console import Console
from rich.table import Table

console = Console()


async def main():
    """Debug the detection."""
    settings = Settings()
    init_database(settings.database.url)

    # Query the test data
    with get_db_context() as session:
        prices = (
            session.query(Price)
            .filter(Price.symbol == "BTC-USD", Price.source == "test_demo")
            .order_by(Price.timestamp)
            .all()
        )

        if not prices:
            console.print("[red]No test data found![/red]")
            return

        console.print(f"[green]Found {len(prices)} price records[/green]")
        console.print(f"Time range: {prices[0].timestamp} to {prices[-1].timestamp}\n")

        # Convert to DataFrame
        df = pd.DataFrame([
            {
                "timestamp": p.timestamp,
                "price": p.price,
                "volume": p.volume_24h or 0,
                "symbol": p.symbol
            }
            for p in prices
        ])

        # Show price statistics
        console.print("[cyan]Price Statistics:[/cyan]")
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Min Price", f"${df['price'].min():,.2f}")
        table.add_row("Max Price", f"${df['price'].max():,.2f}")
        table.add_row("Mean Price", f"${df['price'].mean():,.2f}")
        table.add_row("Std Dev", f"${df['price'].std():,.2f}")
        table.add_row("Range", f"{((df['price'].max() - df['price'].min()) / df['price'].min() * 100):.2f}%")
        console.print(table)
        console.print()

        # Test detection
        console.print("[cyan]Running anomaly detection...[/cyan]")
        detector = AnomalyDetector()
        anomaly = await asyncio.to_thread(detector.detect_all, df)

        if anomaly:
            console.print(f"[green]✓ Anomaly detected![/green]")
            console.print(f"  Type: {anomaly.anomaly_type.value}")
            console.print(f"  Confidence: {anomaly.confidence:.2%}")
            console.print(f"  Z-Score: {anomaly.z_score:.2f}")
            console.print(f"  Price Change: {anomaly.price_change_pct:+.2f}%")
            console.print(f"  Time: {anomaly.detected_at}")
        else:
            console.print("[yellow]No anomaly detected[/yellow]")
            console.print(f"[yellow]Threshold: Z-score > {settings.detection.z_score_threshold}[/yellow]")
            console.print(f"[yellow]Lookback: {settings.detection.lookback_window_minutes} minutes[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
