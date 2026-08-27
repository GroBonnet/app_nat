from __future__ import annotations

from pydantic import BaseModel


class Competition(BaseModel):
    id_cpt: int
    name: str | None = None
    city: str | None = None
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    pool_size: int | None = None
    level: str | None = None
    type: str | None = None
    category: str | None = None
    season: str | None = None
    n_results: int | None = None