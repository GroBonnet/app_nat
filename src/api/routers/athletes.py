from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from src.api.db_connection import get_connection
from src.api.filters.athletes_filters import get_athlete_best_times_filters
from src.api.queries.athletes_queries import (
    athlete_best_times_select,
    get_athlete_best_times_conditions,
)
from src.api.queries.competitions_queries import row_to_result
from src.domain.models import (
    AthleteProfile,
    DistanceScore,
    Result,
    Stroke,
    StrokeProfile,
)
from src.domain.schema import swimmer
from src.domain.world_records import get_world_record

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


STROKE_ORDER = [Stroke.NL, Stroke.DOS, Stroke.BRA, Stroke.PAP, Stroke.MEDLEY]


def time_score(wr_time_cs: int, athlete_time_cs: int, exponent: float = 3.0) -> float:
    if wr_time_cs <= 0 or athlete_time_cs <= 0:
        raise ValueError("Les temps doivent être strictement positifs")
    score = 100.0 * (wr_time_cs / athlete_time_cs) ** exponent
    return min(100.0, round(score, 1))


@athlete_router.get(
    "/{iuf}/profile",
    response_model=AthleteProfile,
    summary="Profil noté d'un athlète (score /100 par distance et par nage, vs WR)",
)
def athlete_profile(
    iuf: int,
    pool_size: int = Query(50, description="25 (petit bassin) ou 50 (grand bassin)"),
    conn=Depends(get_connection),
):
    swimmer_row = conn.execute(
        select(swimmer.c.iuf, swimmer.c.full_name, swimmer.c.gender).where(
            swimmer.c.iuf == iuf
        )
    ).first()

    if swimmer_row is None:
        raise HTTPException(404, f"Athlète {iuf} introuvable")

    conds = get_athlete_best_times_conditions(
        iuf=iuf, pool_size=pool_size, include_relays=False
    )
    stmt = athlete_best_times_select(conds)
    rows = [row_to_result(r) for r in conn.execute(stmt).all()]

    by_stroke: dict[str, list[DistanceScore]] = {s.value: [] for s in STROKE_ORDER}
    for r in rows:
        wr = get_world_record(r["stroke"], r["distance"], pool_size, swimmer_row.gender)
        if wr is None:
            continue
        by_stroke[r["stroke"]].append(
            DistanceScore(
                distance=r["distance"],
                time_cs=r["time_cs"],
                time=r["time"],
                wr_time_cs=wr["time_cs"],
                wr_holder=wr["holder"],
                score=time_score(wr["time_cs"], r["time_cs"]),
            )
        )

    strokes = [
        StrokeProfile(
            stroke=s.value,
            distances=sorted(by_stroke[s.value], key=lambda d: d.distance),
            score=(
                round(
                    sum(d.score for d in by_stroke[s.value]) / len(by_stroke[s.value]),
                    1,
                )
                if by_stroke[s.value]
                else None
            ),
        )
        for s in STROKE_ORDER
    ]

    return AthleteProfile(
        iuf=iuf, swimmer=swimmer_row.full_name, pool_size=pool_size, strokes=strokes
    )
