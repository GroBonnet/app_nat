from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.schema import club, competition, event, result, swimmer


def _insert(table, conn):
    """Renvoie le constructeur INSERT du bon dialecte (pour ON CONFLICT)."""
    return (
        pg_insert(table) if conn.dialect.name == "postgresql" else sqlite_insert(table)
    )


def upsert_competitions(conn, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = _insert(competition, conn)
    cols = [c.name for c in competition.c if c.name != "id_cpt"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["id_cpt"],
        set_={c: stmt.excluded[c] for c in cols},
    )
    conn.execute(stmt, rows)


def upsert_clubs(conn, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = _insert(club, conn)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id_club"],
        set_={"name": func.coalesce(stmt.excluded["name"], club.c.name)},
    )
    conn.execute(stmt, rows)


def upsert_swimmers(conn, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = _insert(swimmer, conn)
    cols = [c.name for c in swimmer.c if c.name != "iuf"]
    # on garde la valeur existante si la nouvelle est NULL (COALESCE)
    stmt = stmt.on_conflict_do_update(
        index_elements=["iuf"],
        set_={c: func.coalesce(stmt.excluded[c], swimmer.c[c]) for c in cols},
    )
    conn.execute(stmt, rows)


def upsert_events(conn, rows: list[dict]) -> dict[tuple, int]:
    """Insère les épreuves manquantes et renvoie {(distance, stroke, is_relay): id_event}."""
    if rows:
        stmt = _insert(event, conn).on_conflict_do_nothing(
            index_elements=["distance", "stroke", "is_relay"]
        )
        conn.execute(stmt, rows)
    res = conn.execute(
        select(event.c.id_event, event.c.distance, event.c.stroke, event.c.is_relay)
    )
    return {(d, s, bool(r)): i for (i, d, s, r) in res}


def delete_results_for(conn, id_cpts: list[int]) -> None:
    if not id_cpts:
        return
    conn.execute(result.delete().where(result.c.id_cpt.in_(list(id_cpts))))


def insert_results(conn, rows: list[dict]) -> None:
    if not rows:
        return
    conn.execute(result.insert(), rows)
