from __future__ import annotations

import os

from sqlalchemy import URL, make_url


def get_url(override: str | None = None) -> URL:
    if override:
        return make_url(override)
    if os.getenv("DATABASE_URL"):
        return make_url(os.environ["DATABASE_URL"])
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD") or None,
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "ffn"),
    )
