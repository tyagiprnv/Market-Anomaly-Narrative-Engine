"""Main CLI entry point for Market Anomaly Narrative Engine."""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, UTC

import click
from rich import box
from rich.json import JSON
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from sqlalchemy import create_engine, func, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import selectinload

from config.settings import Settings
from src.cli.utils import async_command, console, run_with_shutdown
from src.database.connection import get_db_context, init_database
from src.database.models import Anomaly, Base, Narrative, NewsArticle
from src.orchestration.pipeline import MarketAnomalyPipeline
from src.orchestration.scheduler import AnomalyDetectionScheduler

# Setup logging with Rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load settings (global singleton)
try:
    settings = Settings()
except Exception as e:
    console.print(f"[red]Failed to load settings:[/red] {e}")
    console.print(
        "\n[yellow]Check your .env file and ensure all required variables are set.[/yellow]"
    )
    sys.exit(1)


@click.group()
@click.version_option(version="0.1.0", prog_name="MANE")
def cli():
    """Market Anomaly Narrative Engine - Detect crypto anomalies and generate AI narratives.

    \b
    Examples:
      mane init-db                    # Initialize database
      mane detect --symbol BTC-USD    # Run detection for one symbol
      mane detect --all               # Run detection for all configured symbols
      mane serve                      # Start continuous monitoring
      mane list-narratives --limit 5  # View recent narratives
      mane list-news --symbol BTC-USD # View news articles
      mane metrics                    # Show performance metrics
    """
    pass


@cli.command()
@click.option(
    "--drop-existing",
    is_flag=True,
    help="Drop existing tables before creating (DANGER: destroys all data)",
)
def init_db(drop_existing):
    """Initialize database schema.

    Creates all required tables: prices, anomalies, news_articles,
    narratives, and news_clusters.
    """
    try:
        console.print("[cyan]Initializing database...[/cyan]")

        # Create engine
        engine = create_engine(settings.database.url)

        # Drop existing tables if requested
        if drop_existing:
            if click.confirm(
                "WARNING: This will DELETE ALL DATA. Are you sure?", abort=True
            ):
                Base.metadata.drop_all(engine)
                console.print("[yellow]Dropped existing tables[/yellow]")

        # Create all tables
        Base.metadata.create_all(engine)
        console.print("[green]Database schema created successfully[/green]")

        # Show created tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if tables:
            table = Table(title="Created Tables", box=box.ROUNDED)
            table.add_column("Table Name", style="cyan")
            table.add_column("Status", style="green")

            for table_name in tables:
                table.add_row(table_name, "✓ Created")

            console.print(table)
            console.print(f"\n[green]Total: {len(tables)} tables[/green]")
        else:
            console.print("[yellow]No tables found[/yellow]")

    except OperationalError as e:
        console.print(f"[red]Database connection failed:[/red] {e}")
        console.print("\n[yellow]Did you:[/yellow]")
        console.print("  1. Start PostgreSQL?")
        console.print("  2. Set DATABASE__PASSWORD in .env?")
        console.print("  3. Create the database?")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to initialize database:[/red] {e}")
        logger.exception("Database initialization failed")
        sys.exit(1)


@cli.command()
@click.option("--symbol", type=str, help="Trading symbol (e.g., BTC-USD)")
@click.option("--all", "detect_all", is_flag=True, help="Run for all configured symbols")
@click.option(
    "--news-mode",
    type=click.Choice(["live", "replay", "hybrid"]),
    help="News aggregation mode (live=RSS/Grok, replay=historical datasets, hybrid=both)",
)
@async_command
async def detect(symbol, detect_all, news_mode):
    """Run anomaly detection pipeline for symbol(s).

    Executes the full Phase 1 → 2 → 3 pipeline:
    - Phase 1: Detect anomaly, fetch and cluster news
    - Phase 2: Generate narrative explanation
    - Phase 3: Validate narrative quality

    \b
    News Modes:
      live   - RSS feeds + Grok (all free, 5-10 min delay)
      replay - Historical JSON datasets (deterministic, cost-free demos)
      hybrid - Both live and replay sources
    """
    # Validate arguments
    if not symbol and not detect_all:
        console.print("[red]Error: Specify either --symbol or --all[/red]")
        console.print("\nUsage:")
        console.print("  mane detect --symbol BTC-USD")
        console.print("  mane detect --all")
        sys.exit(1)

    if symbol and detect_all:
        console.print("[red]Error: Cannot use both --symbol and --all[/red]")
        sys.exit(1)

    try:
        # Initialize database
        init_database(settings.database.url)

        # Create pipeline with news mode
        pipeline = MarketAnomalyPipeline(settings, news_mode=news_mode)

        # Determine symbols to process
        symbols = settings.detection.symbols if detect_all else [symbol]

        console.print(f"\n[cyan]Running detection for {len(symbols)} symbol(s)...[/cyan]\n")

        # Process each symbol
        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for sym in symbols:
                task = progress.add_task(f"Processing {sym}...", total=None)

                try:
                    with get_db_context() as session:
                        anomaly, stats = await pipeline.run_for_symbol(sym, session)

                        results.append((sym, anomaly, stats))
                        progress.remove_task(task)

                except Exception as e:
                    console.print(f"[red]✗ [{sym}][/red] Pipeline failed: {e}")
                    logger.exception(f"Pipeline failed for {sym}")
                    progress.remove_task(task)
                    continue

        # Display results
        console.print()
        anomaly_count = 0

        for sym, anomaly, stats in results:
            if stats.anomaly_detected and anomaly:
                anomaly_count += 1

                # Handle detached instances (session closed after pipeline execution)
                try:
                    # Check if narrative exists (it might not if pipeline failed mid-execution)
                    if not hasattr(anomaly, 'narrative') or anomaly.narrative is None:
                        console.print(f"• [{sym}] Anomaly detected but narrative generation failed")
                        continue

                    # Format narrative (truncate if too long)
                    narrative_text = anomaly.narrative.narrative_text
                    if len(narrative_text) > 200:
                        narrative_text = narrative_text[:197] + "..."

                    # Format validation status
                    if anomaly.narrative.validation_passed:
                        validation_status = "[green]✓ VALIDATED[/green]"
                    elif anomaly.narrative.validation_passed is False:
                        validation_status = "[red]✗ REJECTED[/red]"
                    else:
                        validation_status = "[yellow]? UNKNOWN[/yellow]"
                except Exception as e:
                    logger.warning(f"Could not access narrative for {sym}: {e}")
                    console.print(f"• [{sym}] Anomaly detected but narrative data unavailable")
                    continue

                # Create panel
                panel_content = (
                    f"[bold]Type:[/bold] {anomaly.anomaly_type.value}\n"
                    f"[bold]Confidence:[/bold] {anomaly.confidence:.2f}\n"
                    f"[bold]Z-Score:[/bold] {anomaly.z_score:.2f}\n"
                    f"[bold]Price Change:[/bold] {anomaly.price_change_pct:+.2f}%\n"
                    f"[bold]Time:[/bold] {anomaly.detected_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"[bold]Narrative:[/bold] {narrative_text}\n\n"
                    f"[bold]Validation:[/bold] {validation_status}\n"
                    f"[bold]News Articles:[/bold] {stats.news_count}\n"
                    f"[bold]Duration:[/bold] {stats.execution_time_seconds:.1f}s"
                )

                console.print(
                    Panel(
                        panel_content,
                        title=f"[green]✓[/green] Anomaly Detected: {sym}",
                        border_style="green",
                        box=box.ROUNDED,
                    )
                )
            else:
                console.print(f"[dim]• [{sym}][/dim] No anomaly detected")

        # Summary
        console.print(
            f"\n[cyan]Summary:[/cyan] {anomaly_count}/{len(symbols)} symbols had anomalies"
        )

    except OperationalError:
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Detection failed:[/red] {e}")
        logger.exception("Detection command failed")
        sys.exit(1)


@cli.command()
@click.option("--symbol", type=str, help="Trading symbol (e.g., BTC-USD)")
@click.option("--all", "backfill_all", is_flag=True, help="Backfill all configured symbols")
@click.option("--days", type=int, default=7, help="Number of days to backfill (default: 7)")
@async_command
async def backfill(symbol, backfill_all, days):
    """Backfill historical price data from exchange APIs.

    Fetches historical 1-minute candle data and stores it in the database.
    Uses batch insertion for efficiency and skips duplicates automatically.

    Examples:
        mane backfill --symbol BTC-USD --days 7
        mane backfill --all --days 30
    """
    # Validate arguments
    if not symbol and not backfill_all:
        console.print("[red]Error: Specify either --symbol or --all[/red]")
        console.print("\nUsage:")
        console.print("  mane backfill --symbol BTC-USD --days 7")
        console.print("  mane backfill --all --days 7")
        sys.exit(1)

    if symbol and backfill_all:
        console.print("[red]Error: Cannot use both --symbol and --all[/red]")
        sys.exit(1)

    if days <= 0:
        console.print("[red]Error: --days must be positive[/red]")
        sys.exit(1)

    if days > 365:
        console.print("[yellow]Warning: Large backfills may take significant time[/yellow]")
        if not click.confirm("Continue?"):
            sys.exit(0)

    try:
        # Initialize database
        init_database(settings.database.url)

        # Determine which client to use
        from src.phase1_detector.data_ingestion import CoinbaseClient, BinanceClient

        if settings.data_ingestion.primary_source == "coinbase":
            client = CoinbaseClient(
                api_key=settings.data_ingestion.coinbase_api_key,
                api_secret=settings.data_ingestion.coinbase_api_secret,
            )
        else:
            client = BinanceClient(
                api_key=settings.data_ingestion.binance_api_key,
                api_secret=settings.data_ingestion.binance_api_secret,
            )

        # Determine symbols to process
        symbols = settings.detection.symbols if backfill_all else [symbol]

        console.print(
            f"\n[cyan]Starting backfill for {len(symbols)} symbol(s)...[/cyan]"
        )
        console.print(f"[dim]Source: {client.source_name}[/dim]")
        console.print(f"[dim]Date range: {days} days[/dim]")
        console.print(f"[dim]Granularity: 1 minute[/dim]\n")

        # Calculate date range
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Process each symbol with progress tracking
        total_inserted = 0
        total_fetched = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for sym in symbols:
                task = progress.add_task(
                    f"[cyan]Fetching {sym}...[/cyan]", total=None
                )

                try:
                    # Fetch historical data
                    prices = await client.get_historical_prices(
                        symbol=sym,
                        start_time=start_time,
                        end_time=end_time,
                        granularity_seconds=60,
                    )

                    total_fetched += len(prices)

                    # Update progress
                    progress.update(
                        task,
                        description=f"[cyan]Storing {sym} ({len(prices)} records)...[/cyan]",
                    )

                    # Store in database
                    with get_db_context() as session:
                        inserted = await client.store_prices_bulk(
                            prices, session, batch_size=1000
                        )
                        total_inserted += inserted

                    # Success message
                    skipped = len(prices) - inserted
                    progress.update(
                        task,
                        description=(
                            f"[green]✓ {sym}[/green]: "
                            f"{inserted} inserted, {skipped} skipped (duplicates)"
                        ),
                    )

                    await asyncio.sleep(0.5)  # Brief pause for readability
                    progress.remove_task(task)

                except ValueError as e:
                    progress.update(task, description=f"[red]✗ {sym}[/red]: {e}")
                    await asyncio.sleep(1)
                    progress.remove_task(task)
                    continue

                except ConnectionError as e:
                    progress.update(
                        task, description=f"[red]✗ {sym}[/red]: API connection failed"
                    )
                    logger.exception(f"Connection error for {sym}")
                    await asyncio.sleep(1)
                    progress.remove_task(task)
                    continue

                except Exception as e:
                    progress.update(
                        task, description=f"[red]✗ {sym}[/red]: {str(e)[:50]}"
                    )
                    logger.exception(f"Backfill failed for {sym}")
                    await asyncio.sleep(1)
                    progress.remove_task(task)
                    continue

        # Close client
        await client.close()

        # Summary
        console.print()
        console.print(
            Panel(
                f"[bold]Fetched:[/bold] {total_fetched:,} records\n"
                f"[bold]Inserted:[/bold] {total_inserted:,} new records\n"
                f"[bold]Skipped:[/bold] {total_fetched - total_inserted:,} duplicates\n"
                f"[bold]Symbols:[/bold] {len(symbols)}",
                title="[green]Backfill Complete[/green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )

    except OperationalError:
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Backfill failed:[/red] {e}")
        logger.exception("Backfill command failed")
        sys.exit(1)


@cli.command("backfill-news")
@click.option("--symbol", required=True, help="Trading symbol (e.g., BTC-USD)")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option(
    "--source",
    type=click.Choice(["manual"]),
    default="manual",
    help="Data source (manual=provide JSON/CSV file path)",
)
@click.option(
    "--file-path",
    type=click.Path(exists=True),
    help="Path to JSON/CSV file containing news data",
)
def backfill_news(symbol, start_date, end_date, source, file_path):
    """Backfill historical news data for replay mode.

    Creates standardized JSON datasets in datasets/news/ directory for
    deterministic testing and demos.

    \b
    Example:
      mane backfill-news --symbol BTC-USD --start-date 2024-01-01 \\
          --end-date 2024-01-31 --file-path news_data.json

    \b
    Expected JSON format:
      {
        "articles": [
          {
            "title": "...",
            "url": "...",
            "published_at": "2024-01-01T12:00:00Z",
            "source": "coindesk",
            "summary": "...",
            "sentiment": 0.5
          }
        ]
      }
    """
    import json
    from pathlib import Path
    from datetime import datetime

    try:
        # Validate dates
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            sys.exit(1)

        if start_dt > end_dt:
            console.print("[red]Start date must be before end date[/red]")
            sys.exit(1)

        # Check if file path provided
        if source == "manual" and not file_path:
            console.print("[red]Error: --file-path required for manual source[/red]")
            sys.exit(1)

        # Load input data
        console.print(f"[cyan]Loading data from {file_path}...[/cyan]")
        with open(file_path, "r") as f:
            input_data = json.load(f)

        if "articles" not in input_data:
            console.print("[red]Invalid format: missing 'articles' field[/red]")
            sys.exit(1)

        articles = input_data["articles"]
        console.print(f"[green]Loaded {len(articles)} articles[/green]")

        # Filter articles by date range
        filtered_articles = []
        for article in articles:
            pub_at = datetime.fromisoformat(
                article["published_at"].replace("Z", "+00:00")
            )
            if start_dt <= pub_at <= end_dt:
                # Ensure required fields and add symbol
                if "symbols" not in article:
                    article["symbols"] = [symbol]
                elif symbol not in article["symbols"]:
                    article["symbols"].append(symbol)
                filtered_articles.append(article)

        console.print(
            f"[cyan]Filtered to {len(filtered_articles)} articles in date range[/cyan]"
        )

        # Create output directory
        output_dir = Path(settings.news.replay_dataset_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create output file
        output_file = output_dir / f"{symbol}_{start_date}.json"

        # Create dataset structure
        dataset = {
            "symbol": symbol,
            "date": start_date,
            "articles": filtered_articles,
        }

        # Write to file
        with open(output_file, "w") as f:
            json.dump(dataset, f, indent=2)

        console.print(f"\n[green]✓ Created dataset: {output_file}[/green]")
        console.print(f"[green]  Articles: {len(filtered_articles)}[/green]")
        console.print(f"[green]  Date range: {start_date} to {end_date}[/green]")
        console.print(
            f"\n[yellow]Use with: mane detect --symbol {symbol} --news-mode replay[/yellow]"
        )

    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON format:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to backfill news:[/red] {e}")
        logger.exception("Backfill news command failed")
        sys.exit(1)


@cli.command()
@click.option("--interval", type=int, help="Poll interval in seconds (overrides config)")
@click.option(
    "--news-mode",
    type=click.Choice(["live", "replay", "hybrid"]),
    help="News aggregation mode (live=RSS/Grok, replay=historical datasets, hybrid=both)",
)
@async_command
async def serve(interval, news_mode):
    """Start continuous anomaly detection scheduler.

    Runs two periodic jobs:
    - Price storage: Every 60 seconds
    - Anomaly detection: Every poll_interval seconds (default from config)

    Press Ctrl+C to stop gracefully.

    \b
    News Modes:
      live   - RSS feeds + Grok (all free, 5-10 min delay)
      replay - Historical JSON datasets (deterministic, cost-free demos)
      hybrid - Both live and replay sources
    """
    try:
        # Override interval if provided
        if interval:
            settings.data_ingestion.poll_interval_seconds = interval

        # Initialize database
        init_database(settings.database.url)

        # Create scheduler with news mode
        scheduler = AnomalyDetectionScheduler(settings, news_mode=news_mode)

        # Display startup info
        console.print(
            Panel(
                f"[green]Monitoring {len(settings.detection.symbols)} symbols[/green]\n\n"
                f"[bold]Symbols:[/bold] {', '.join(settings.detection.symbols)}\n"
                f"[bold]Poll Interval:[/bold] {settings.data_ingestion.poll_interval_seconds}s\n"
                f"[bold]Price Storage:[/bold] Every 60s\n\n"
                f"[yellow]Press Ctrl+C to stop[/yellow]",
                title="MANE Scheduler",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

        # Run scheduler with graceful shutdown
        await run_with_shutdown(scheduler, console)

    except OperationalError:
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Scheduler failed:[/red] {e}")
        logger.exception("Serve command failed")
        sys.exit(1)


@cli.command()
@click.option("--limit", type=int, default=10, help="Number of narratives to show")
@click.option("--symbol", type=str, help="Filter by trading symbol")
@click.option("--validated-only", is_flag=True, help="Show only validated narratives")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def list_narratives(limit, symbol, validated_only, format):
    """List recent narratives from the database.

    Shows narrative text, validation status, anomaly details, and timing.
    """
    try:
        # Initialize database
        init_database(settings.database.url)

        with get_db_context() as session:
            # Build query
            query = (
                session.query(Narrative)
                .join(Anomaly)
                .options(selectinload(Narrative.anomaly))
                .order_by(Narrative.created_at.desc())
            )

            # Apply filters
            if symbol:
                query = query.filter(Anomaly.symbol == symbol)

            if validated_only:
                query = query.filter(Narrative.validation_passed == True)

            # Execute query
            narratives = query.limit(limit).all()

            if not narratives:
                console.print("[yellow]No narratives found[/yellow]")
                if validated_only:
                    console.print("[dim]Try without --validated-only[/dim]")
                return

            # Output based on format
            if format == "json":
                # JSON output
                data = [
                    {
                        "id": str(n.id),
                        "symbol": n.anomaly.symbol,
                        "detected_at": n.anomaly.detected_at.isoformat(),
                        "anomaly_type": n.anomaly.anomaly_type.value,
                        "confidence": float(n.anomaly.confidence),
                        "narrative": n.narrative_text,
                        "validation_passed": n.validation_passed,
                        "created_at": n.created_at.isoformat(),
                    }
                    for n in narratives
                ]
                console.print(JSON.from_data(data))

            else:
                # Table output
                table = Table(
                    title=f"Recent Narratives ({len(narratives)})",
                    box=box.ROUNDED,
                    show_lines=True,
                )
                table.add_column("Symbol", style="cyan", no_wrap=True)
                table.add_column("Time", style="magenta", no_wrap=True)
                table.add_column("Type", style="yellow")
                table.add_column("Narrative", style="green", max_width=50)
                table.add_column("Valid", justify="center", no_wrap=True)

                for n in narratives:
                    # Format validation status
                    if n.validation_passed is True:
                        validation_icon = "[green]✓[/green]"
                    elif n.validation_passed is False:
                        validation_icon = "[red]✗[/red]"
                    else:
                        validation_icon = "[yellow]?[/yellow]"

                    # Truncate narrative if too long
                    narrative_text = n.narrative_text
                    if len(narrative_text) > 150:
                        narrative_text = narrative_text[:147] + "..."

                    table.add_row(
                        n.anomaly.symbol,
                        n.anomaly.detected_at.strftime("%Y-%m-%d %H:%M"),
                        n.anomaly.anomaly_type.value,
                        narrative_text,
                        validation_icon,
                    )

                console.print(table)

    except (OperationalError, ProgrammingError):
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to list narratives:[/red] {e}")
        logger.exception("List narratives command failed")
        sys.exit(1)


@cli.command()
@click.option("--limit", type=int, default=20, help="Number of articles to show")
@click.option("--symbol", type=str, help="Filter by trading symbol")
@click.option("--anomaly-id", type=str, help="Filter by anomaly ID")
@click.option("--source", type=str, help="Filter by news source")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def list_news(limit, symbol, anomaly_id, source, format):
    """List news articles from the database.

    Shows news articles linked to anomalies with sentiment, timing, and source info.
    """
    try:
        # Initialize database
        init_database(settings.database.url)

        with get_db_context() as session:
            # Build query
            query = (
                session.query(NewsArticle)
                .join(Anomaly)
                .options(selectinload(NewsArticle.anomaly))
                .order_by(NewsArticle.published_at.desc())
            )

            # Apply filters
            if symbol:
                query = query.filter(Anomaly.symbol == symbol)

            if anomaly_id:
                query = query.filter(NewsArticle.anomaly_id == anomaly_id)

            if source:
                query = query.filter(NewsArticle.source == source)

            # Execute query
            articles = query.limit(limit).all()

            if not articles:
                console.print("[yellow]No news articles found[/yellow]")
                if symbol or anomaly_id or source:
                    console.print("[dim]Try without filters[/dim]")
                return

            # Output based on format
            if format == "json":
                # JSON output
                data = [
                    {
                        "id": str(a.id),
                        "anomaly_id": str(a.anomaly_id),
                        "symbol": a.anomaly.symbol,
                        "source": a.source,
                        "title": a.title,
                        "url": a.url,
                        "published_at": a.published_at.isoformat(),
                        "summary": a.summary,
                        "sentiment": a.sentiment if hasattr(a, 'sentiment') else None,
                        "timing_tag": a.timing_tag,
                        "time_diff_minutes": a.time_diff_minutes,
                        "cluster_id": a.cluster_id,
                    }
                    for a in articles
                ]
                console.print(JSON.from_data(data))

            else:
                # Table output
                table = Table(
                    title=f"News Articles ({len(articles)})",
                    box=box.ROUNDED,
                    show_lines=True,
                )
                table.add_column("Symbol", style="cyan", no_wrap=True)
                table.add_column("Published", style="magenta", no_wrap=True)
                table.add_column("Source", style="yellow", no_wrap=True)
                table.add_column("Title", style="green", max_width=40)
                table.add_column("Sentiment", justify="center", no_wrap=True)
                table.add_column("Timing", justify="center", no_wrap=True)

                for a in articles:
                    # Format sentiment
                    sentiment_val = a.sentiment if hasattr(a, 'sentiment') else None
                    if sentiment_val is not None:
                        if sentiment_val > 0.2:
                            sentiment_str = f"[green]+{sentiment_val:.2f}[/green]"
                        elif sentiment_val < -0.2:
                            sentiment_str = f"[red]{sentiment_val:.2f}[/red]"
                        else:
                            sentiment_str = f"[dim]{sentiment_val:.2f}[/dim]"
                    else:
                        sentiment_str = "[dim]N/A[/dim]"

                    # Format timing
                    if a.timing_tag == "pre_event":
                        timing_str = f"[yellow]Pre ({a.time_diff_minutes:.0f}m)[/yellow]"
                    elif a.timing_tag == "post_event":
                        timing_str = f"[blue]Post (+{a.time_diff_minutes:.0f}m)[/blue]"
                    else:
                        timing_str = "[dim]N/A[/dim]"

                    # Truncate title if too long
                    title = a.title
                    if len(title) > 70:
                        title = title[:67] + "..."

                    table.add_row(
                        a.anomaly.symbol,
                        a.published_at.strftime("%m-%d %H:%M"),
                        a.source,
                        title,
                        sentiment_str,
                        timing_str,
                    )

                console.print(table)

                # Show summary stats
                console.print()
                sources = {}
                sentiments = []
                for a in articles:
                    sources[a.source] = sources.get(a.source, 0) + 1
                    if hasattr(a, 'sentiment') and a.sentiment is not None:
                        sentiments.append(a.sentiment)

                console.print(f"[cyan]Sources:[/cyan] {', '.join(f'{k}({v})' for k, v in sources.items())}")
                if sentiments:
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    console.print(f"[cyan]Average Sentiment:[/cyan] {avg_sentiment:.2f}")

    except (OperationalError, ProgrammingError):
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to list news:[/red] {e}")
        logger.exception("List news command failed")
        sys.exit(1)


@cli.command()
@click.option("--symbol", type=str, help="Show metrics for specific symbol")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def metrics(symbol, format):
    """Show performance metrics from database.

    Displays aggregate statistics about anomaly detection and narrative
    generation from the database.
    """
    try:
        # Initialize database
        init_database(settings.database.url)

        with get_db_context() as session:
            # Build base queries
            anomaly_query = session.query(func.count(Anomaly.id))
            narrative_query = session.query(func.count(Narrative.id))
            validated_query = session.query(func.count(Narrative.id)).filter(
                Narrative.validation_passed == True
            )
            rejected_query = session.query(func.count(Narrative.id)).filter(
                Narrative.validation_passed == False
            )

            # Apply symbol filter if provided
            if symbol:
                anomaly_query = anomaly_query.filter(Anomaly.symbol == symbol)
                narrative_query = narrative_query.join(Anomaly).filter(
                    Anomaly.symbol == symbol
                )
                validated_query = validated_query.join(Anomaly).filter(
                    Anomaly.symbol == symbol
                )
                rejected_query = rejected_query.join(Anomaly).filter(
                    Anomaly.symbol == symbol
                )

            # Execute queries
            total_anomalies = anomaly_query.scalar() or 0
            total_narratives = narrative_query.scalar() or 0
            validated = validated_query.scalar() or 0
            rejected = rejected_query.scalar() or 0

            # Calculate rates
            validation_rate = (validated / total_narratives * 100) if total_narratives else 0
            rejection_rate = (rejected / total_narratives * 100) if total_narratives else 0

            # Output based on format
            if format == "json":
                data = {
                    "symbol": symbol if symbol else "all",
                    "total_anomalies": total_anomalies,
                    "total_narratives": total_narratives,
                    "validated_narratives": validated,
                    "rejected_narratives": rejected,
                    "validation_rate_pct": round(validation_rate, 2),
                    "rejection_rate_pct": round(rejection_rate, 2),
                }
                console.print(JSON.from_data(data))

            else:
                # Table output
                title = f"MANE Performance Metrics - {symbol}" if symbol else "MANE Performance Metrics"
                table = Table(title=title, box=box.ROUNDED)
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green", justify="right")

                table.add_row("Total Anomalies", str(total_anomalies))
                table.add_row("Generated Narratives", str(total_narratives))
                table.add_row("Validated Narratives", str(validated))
                table.add_row("Rejected Narratives", str(rejected))
                table.add_row("Validation Rate", f"{validation_rate:.1f}%")
                table.add_row("Rejection Rate", f"{rejection_rate:.1f}%")

                console.print(table)

                # Show warning if no data
                if total_anomalies == 0:
                    console.print(
                        "\n[yellow]No data yet. Run 'mane detect' or 'mane serve' to start detecting anomalies.[/yellow]"
                    )

    except (OperationalError, ProgrammingError):
        console.print("[red]Database connection failed[/red]")
        console.print("\n[yellow]Did you run 'mane init-db'?[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to retrieve metrics:[/red] {e}")
        logger.exception("Metrics command failed")
        sys.exit(1)


if __name__ == "__main__":
    cli()
