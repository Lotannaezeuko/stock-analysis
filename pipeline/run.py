"""Entry point: python -m pipeline.run [SYMBOL ...]"""
import logging
import sys
from contextlib import closing
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pipeline.config import load_settings
from pipeline.db import finish_run, get_active_symbols, get_connection, start_run
from pipeline.extract import fetch_daily_prices
from pipeline.load import upsert_daily_prices
from pipeline.transform import check_freshness, to_daily_price_rows

# Explicit name: under `python -m pipeline.run`, __name__ would be "__main__"
logger = logging.getLogger("pipeline.run")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FORMAT = "%(asctime)s %(levelname)s [run %(run_id)s] %(name)s: %(message)s"


class _RunContext(logging.Filter):
    """Stamps every log line with the current run_id, so one run's lines can be grepped."""

    run_id = "-"

    def filter(self, record):
        record.run_id = self.run_id
        return True


_run_context = _RunContext()


def configure_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        # Rotate at ~1 MB, keeping 5 old files, so the log can't fill the disk
        RotatingFileHandler(LOG_DIR / "pipeline.log", maxBytes=1_000_000, backupCount=5),
    ]
    for handler in handlers:
        handler.addFilter(_run_context)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.basicConfig(level=logging.INFO, handlers=handlers)


def run_status(attempted: int, failed: int) -> str:
    if attempted == 0 or failed == attempted:
        return "failed"
    return "partial" if failed else "succeeded"


def process_symbol(conn, symbol: str, api_key: str, run_id: int | None = None) -> int:
    """Extract -> transform -> load one symbol's daily prices. Returns rows loaded."""
    series = fetch_daily_prices(symbol, api_key)
    rows, rejected = to_daily_price_rows(symbol, series)

    for reason in rejected:
        logger.warning("Rejected bar: %s", reason)
    if not rows:
        # Every single day failed validation: treat as a failure, not a quiet success
        raise ValueError(f"{symbol}: no valid rows out of {len(series)}")
    check_freshness(symbol, rows, today=date.today())

    loaded = upsert_daily_prices(conn, rows, run_id)
    logger.info("%s: %d rows loaded, %d rejected", symbol, loaded, len(rejected))
    return loaded


def _select_symbols(conn, only: list[str] | None) -> list[str]:
    symbols = get_active_symbols(conn)
    if only:
        # Re-run a subset, e.g. yesterday's failures, without spending the whole API budget
        not_active = sorted(set(only) - set(symbols))
        if not_active:
            logger.warning("Skipping symbols that aren't active: %s", ", ".join(not_active))
        symbols = [s for s in symbols if s in only]
    return symbols


def run(api_key: str, database_url: str, only: list[str] | None = None) -> str:
    """Process active symbols (or just `only`), record the run in pipeline_runs, return its status."""
    with closing(get_connection(database_url)) as conn:
        run_id = start_run(conn)
        _run_context.run_id = run_id
        symbols, errors, total_rows = [], {}, 0

        try:
            symbols = _select_symbols(conn, only)
            logger.info("Run started: %d symbols to process", len(symbols))
            for symbol in symbols:
                # One bad symbol shouldn't stop the rest from loading
                try:
                    total_rows += process_symbol(conn, symbol, api_key, run_id)
                except Exception as e:
                    errors[symbol] = str(e)
                    logger.exception("Failed to process %s", symbol)
        except Exception as e:
            # Something outside the per-symbol loop broke: still record the run as failed
            conn.rollback()
            finish_run(conn, run_id, "failed", len(symbols), len(errors), total_rows, f"run crashed: {e!r}")
            raise

        status = run_status(len(symbols), len(errors))
        error = "; ".join(f"{s}: {msg}" for s, msg in errors.items()) or (
            None if symbols else "no active symbols to process"
        )
        finish_run(conn, run_id, status, len(symbols), len(errors), total_rows, error)
        logger.info(
            "Run %s: %d succeeded, %d failed, %d rows loaded",
            status, len(symbols) - len(errors), len(errors), total_rows,
        )
    return status


def main() -> int:
    configure_logging()
    try:
        settings = load_settings()
        only = [arg.upper() for arg in sys.argv[1:]]
        status = run(settings.api_key, settings.database_url, only)
    except Exception:
        logger.exception("Pipeline crashed")
        return 1
    # Non-zero exit code tells the scheduler (cron, CI) that the run needs attention
    return 0 if status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
