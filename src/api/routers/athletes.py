from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.api.db_connection import get_connection
from src.api.filters.athletes_filters import get_athlete_best_times_filters
from src.api.queries.athletes_queries import (
    athlete_best_times_select,
    get_athlete_best_times_conditions,
)
from src.api.queries.competitions_queries import row_to_result
from src.domain.models import Result
from src.domain.schema import swimmer

athlete_router = APIRouter(prefix="/athletes", tags=["Athletes"])


@athlete_router.get(
    "/{iuf}/best-times",
    response_model=list[Result],
    summary="Meilleurs temps d'un athlète (par distance, nage et bassin)",
)
def athlete_best_times(
    iuf: int,
    filters: dict = Depends(get_athlete_best_times_filters),
    conn=Depends(get_connection),
):
    if conn.execute(select(swimmer.c.iuf).where(swimmer.c.iuf == iuf)).first() is None:
        raise HTTPException(404, f"Athlète {iuf} introuvable")

    conds = get_athlete_best_times_conditions(iuf=iuf, **filters)
    stmt = athlete_best_times_select(conds)
    rows = conn.execute(stmt).all()
    return [row_to_result(r) for r in rows]
