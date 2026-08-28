from __future__ import annotations

from sqlalchemy import func, select

from src.api.queries.competitions_queries import _COLUMNS, _JOIN
from src.domain.models import Stroke
from src.domain.schema import competition, event, result


# ----------------------------- Conditions and queries for athletes/{iuf}/best-times -----------------------------
def get_athlete_best_times_conditions(
    iuf,
    stroke: Stroke | None = None,
    pool_size=None,
    include_relays: bool = False,
):
    conds = [result.c.iuf == iuf, result.c.time_cs.is_not(None)]
    if stroke:
        conds.append(event.c.stroke == stroke.value)
    if pool_size:
        conds.append(competition.c.pool_size == pool_size)
    if not include_relays:
        conds.append(event.c.is_relay.is_(False))
    return conds


def athlete_best_times_select(conds):
    rn = (
        func.row_number()
        .over(
            partition_by=(event.c.distance, event.c.stroke, competition.c.pool_size),
            order_by=result.c.time_cs.asc(),
        )
        .label("rn")
    )
    ranked = select(*_COLUMNS, rn).select_from(_JOIN).where(*conds).subquery("ranked")
    best_cols = [c for c in ranked.c if c.name != "rn"]
    return (
        select(*best_cols)
        .where(ranked.c.rn == 1)
        .order_by(ranked.c.pool_size, ranked.c.distance, ranked.c.stroke)
    )
