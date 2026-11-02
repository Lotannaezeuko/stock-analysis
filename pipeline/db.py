import psycopg2


def get_connection(database_url: str):
    return psycopg2.connect(database_url)


def get_active_symbols(conn) -> list[str]:
    # The symbols table is the single source of truth for which stocks we track
    with conn.cursor() as cur:
        cur.execute("SELECT symbol FROM symbols WHERE is_active ORDER BY symbol")
        return [row[0] for row in cur.fetchall()]
