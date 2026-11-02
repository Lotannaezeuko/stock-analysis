"""Entry point: python -m pipeline.run"""
import logging
import sys
from contextlib import closing
from datetime import date

from pipeline.config import load_settings
from pipeline.db import get_active_symbols, get_connection
from pipeline.extract import fetch_daily_prices
from pipeline.load import upsert_daily_prices
from pipeline.transform import check_freshness, to_daily_price_rows

logger = logging.getLogger(__name__)


def process_symbol(conn, symbol: str, api_key: str) -> int:
    """Extract -> transform -> load one symbol's daily prices. Returns rows loaded."""
    series = fetch_daily_prices(symbol, api_key)
    rows, rejected = to_daily_price_rows(symbol, series)

    for reason in rejected:
        logger.warning("Rejected bar: %s", reason)
    if not rows:
        # Every single day failed validation: treat as a failure, not a quiet success
        raise ValueError(f"{symbol}: no valid rows out of {len(series)}")
    check_freshness(symbol, rows, today=date.today())

    loaded = upsert_daily_prices(conn, rows)
    logger.info("%s: %d rows loaded, %d rejected", symbol, loaded, len(rejected))
    return loaded


def run(api_key: str, database_url: str, only: list[str] | None = None) -> int:
    """Process active symbols (or just `only`, if given). Returns the number of symbols that failed."""
    failures = 0
    total_rows = 0
    with closing(get_connection(database_url)) as conn:
        symbols = get_active_symbols(conn)
        if only:
            # Re-run a subset, e.g. yesterday's failures, without spending the whole API budget
            not_active = sorted(set(only) - set(symbols))
            if not_active:
                logger.warning("Skipping symbols that aren't active: %s", ", ".join(not_active))
            symbols = [s for s in symbols if s in only]
        logger.info("Processing %d active symbols", len(symbols))
        for symbol in symbols:
            # One bad symbol shouldn't stop the rest from loading
            try:
                total_rows += process_symbol(conn, symbol, api_key)
            except Exception:
                failures += 1
                logger.exception("Failed to process %s", symbol)
    logger.info(
        "Finished: %d succeeded, %d failed, %d rows loaded",
        len(symbols) - failures, failures, total_rows,
    )
    return failures


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    # Optional: python -m pipeline.run AMZN CL  -> only process those symbols
    only = [arg.upper() for arg in sys.argv[1:]]
    failures = run(settings.api_key, settings.database_url, only)
    # Non-zero exit code tells a scheduler (cron, GitHub Actions) the run failed
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
