import psycopg2


def get_connection(database_url: str):
    return psycopg2.connect(database_url)


def get_active_symbols(conn) -> list[str]:
    # The symbols table is the single source of truth for which stocks we track.
    # `with conn` ends the read's transaction here instead of leaving it open
    # for the whole run (which froze now() timestamps at the run's start).
    with conn, conn.cursor() as cur:
        cur.execute("SELECT symbol FROM symbols WHERE is_active ORDER BY symbol")
        return [row[0] for row in cur.fetchall()]


def start_run(conn) -> int:
    """Record the start of a pipeline run and return its run_id."""
    with conn, conn.cursor() as cur:
        cur.execute("INSERT INTO pipeline_runs DEFAULT VALUES RETURNING run_id")
        return cur.fetchone()[0]


def finish_run(conn, run_id: int, status: str, attempted: int, failed: int,
               rows_loaded: int, error: str | None = None) -> None:
    """Record how a pipeline run ended, so failures are visible with one query."""
    with conn, conn.cursor() as cur:
        # clock_timestamp() is the real current time; now() is when the
        # current transaction began, which can be long before the run ended.
        cur.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = clock_timestamp(), status = %s, symbols_attempted = %s,
                symbols_failed = %s, rows_loaded = %s, error = %s
            WHERE run_id = %s
            """,
            (status, attempted, failed, rows_loaded, error, run_id),
        )
