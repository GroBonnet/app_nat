"""Moteur SQLAlchemy et gestion du schéma (création base + tables)."""
from __future__ import annotations

import logging

from sqlalchemy import URL, create_engine, text

from src.infrastructure.config import get_url
from src.domain.schema import metadata

log = logging.getLogger("pg.database")


def make_engine(url: URL | str | None = None, echo: bool = False):
    return create_engine(get_url(url) if not isinstance(url, URL) else url,
                         echo=echo, future=True)


def ensure_database(url: URL | str | None = None) -> bool:
    """Crée la base cible si besoin (PostgreSQL)
    Retourne True si la base a été créée.
    """
    u = get_url(url) if not isinstance(url, URL) else url
    
    if u.get_backend_name() != "postgresql":
        return False  # SQLite : le fichier est créé automatiquement
    admin = create_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT",
                          future=True)
    try:
        with admin.connect() as c:
            exists = c.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": u.database},
            ).scalar()
            if exists:
                log.info("La base %s existe déjà.", u.database)
                return False
            c.execute(text(f'CREATE DATABASE "{u.database}"'))
            log.info("Base %s créée.", u.database)
            return True
    finally:
        admin.dispose()


def init_schema(engine) -> None:
    metadata.create_all(engine)
    log.info("Schéma appliqué.")


def drop_schema(engine) -> None:
    metadata.drop_all(engine)
    log.info("Tables supprimées.")
