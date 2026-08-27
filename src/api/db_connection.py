"""Connexion à la base pour l'API (réutilise la config du module `pg`)."""
from __future__ import annotations

import functools

from sqlalchemy.engine import Connection

from src.infrastructure.config import get_url
from src.infrastructure.database import make_engine


@functools.lru_cache(maxsize=1)
def get_engine():
    """Un seul Engine pour toute la durée de vie du process."""
    return make_engine(get_url())


def get_connection() -> Connection:
    """Dépendance FastAPI : fournit une connexion, refermée après la requête."""
    with get_engine().connect() as conn:
        yield conn
