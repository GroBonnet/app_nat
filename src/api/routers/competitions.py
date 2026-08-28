from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from src.api.db_connection import get_connection
from src.api.filters.competitions_filters import (
    get_competition_list_filters,
    get_competition_result_filters,
    get_competition_result_sorting,
)
from src.api.queries.competitions_queries import (
    competitions_select,
    count_select,
    get_competition_list_conditions,
    get_competition_result_conditions,
    results_select,
    row_to_result,
)
from src.domain.models import Competition, ResultsPage
from src.domain.schema import competition

competition_router = APIRouter(prefix="/competitions", tags=["compétitions"])


_COMP_FIELDS = (
    "id_cpt",
    "name",
    "city",
    "country",
    "date_start",
    "date_end",
    "pool_size",
    "level",
    "type",
    "category",
    "season",
)


def _comp_dict(row) -> dict:
    m = row._mapping
    d = {k: m[k] for k in _COMP_FIELDS}
    for k in ("date_start", "date_end"):
        if d.get(k) is not None:
            d[k] = str(d[k])
    d["n_results"] = m.get("n_results")
    return d


@competition_router.get(
    "", response_model=list[Competition], summary="Lister / filtrer les compétitions"
)
def list_competitions(
    filters: dict = Depends(get_competition_list_filters),
    conn=Depends(get_connection),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conds = get_competition_list_conditions(**filters)
    stmt = competitions_select(conds, limit, offset)
    rows = conn.execute(stmt).all()
    return [_comp_dict(r) for r in rows]


@competition_router.get(
    "/{id_cpt}/results",
    response_model=ResultsPage,
    summary="Résultats d'une compétition (filtrables)",
)
def competition_results(
    id_cpt: int,
    filters: dict = Depends(get_competition_result_filters),
    sort: dict = Depends(get_competition_result_sorting),
    conn=Depends(get_connection),
):
    if (
        conn.execute(
            select(competition.c.id_cpt).where(competition.c.id_cpt == id_cpt)
        ).first()
        is None
    ):
        raise HTTPException(404, f"Compétition {id_cpt} introuvable")

    conds = get_competition_result_conditions(id_cpt=id_cpt, **filters)
    total = conn.execute(count_select(conds)).scalar_one()
    rows = conn.execute(results_select(conds, sort["limit"], sort["offset"])).all()
    return ResultsPage(
        total=total,
        limit=sort["limit"],
        offset=sort["offset"],
        items=[row_to_result(r) for r in rows],
    )
