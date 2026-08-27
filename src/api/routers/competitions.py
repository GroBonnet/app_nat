from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from src.domain.models import Competition
from src.api.db_connection import get_connection
from src.domain.schema import competition, result


competition_router = APIRouter(prefix="/competitions", tags=["compétitions"])


_COMP_FIELDS = ("id_cpt", "name", "city", "country", "date_start", "date_end",
                "pool_size", "level", "type", "category", "season")


def _comp_dict(row) -> dict:
    m = row._mapping
    d = {k: m[k] for k in _COMP_FIELDS}
    for k in ("date_start", "date_end"):
        if d.get(k) is not None:
            d[k] = str(d[k])
    d["n_results"] = m.get("n_results")
    return d


@competition_router.get("", response_model=list[Competition], summary="Lister / filtrer les compétitions")
def list_competitions(
    year: int | None = Query(None, description="Année civile"),
    level: str | None = None,
    category: str | None = None,
    pool_size: int | None = Query(None, description="25 ou 50"),
    search: str | None = Query(None, description="Recherche dans le nom"),
    limit: int = Query(100, ge=1, le=500),
    conn=Depends(get_connection),
):
    conds = []
    if year:
        conds += [competition.c.date_start >= date(year, 1, 1),
                  competition.c.date_start <= date(year, 12, 31)]
    if level:
        conds.append(competition.c.level == level)
    if category:
        conds.append(competition.c.category == category)
    if pool_size:
        conds.append(competition.c.pool_size == pool_size)
    if search:
        conds.append(competition.c.name.ilike(f"%{search}%"))

    n_sub = (select(func.count()).select_from(result)
             .where(result.c.id_cpt == competition.c.id_cpt)
             .scalar_subquery().label("n_results"))
    stmt = (select(competition, n_sub).where(*conds)
            .order_by(competition.c.date_start.desc().nullslast())
            .limit(limit))
    return [_comp_dict(r) for r in conn.execute(stmt).all()]