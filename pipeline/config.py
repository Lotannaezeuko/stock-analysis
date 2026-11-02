import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# The list of stocks to track lives in the `symbols` table, not here.
# See pipeline/sql/seed_symbols.sql for the initial list.


@dataclass(frozen=True)
class Settings:
    api_key: str
    database_url: str


def load_settings() -> Settings:
    # Fail fast with a clear message rather than sending "apikey=None" to the API
    missing = [name for name in ("ALPHA_VANTAGE_API_KEY", "DATABASE_URL") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    return Settings(
        api_key=os.environ["ALPHA_VANTAGE_API_KEY"],
        database_url=os.environ["DATABASE_URL"],
    )
