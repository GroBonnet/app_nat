from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from src.domain.models import Gender, Phase, Stroke
from src.domain.schema import club, competition, event, result, swimmer


# ----------------------------- Conditions and queries for list competitions -----------------------------
def get_competition_list_conditions(
    year=None, level=None, category=None, pool_size=None, competition_name=None
):
    conds = []

    if year is not None:
        conds.append(competition.c.date_start >= date(year, 1, 1))
        conds.append(competition.c.date_start <= date(year, 12, 31))
    if level:
        conds.append(competition.c.level == level)
    if pool_size:
        conds.append(competition.c.pool_size == pool_size)
    if category:
        conds.append(competition.c.category == category)
    if competition_name:
        conds.append(swimmer.c.full_name.ilike(f"%{competition_name}%"))
    return conds


def competitions_select(conds, limit: int, offset: int = 0):
    n_sub = (
        select(func.count())
        .select_from(result)
        .where(result.c.id_cpt == competition.c.id_cpt)
        .scalar_subquery()
        .label("n_results")
    )
    return (
        select(competition, n_sub)
        .where(*conds)
        .order_by(competition.c.date_start.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )


# ----------------------------- Conditions and queries for competition/{id_cpt}/results -----------------------------
def get_competition_result_conditions(
    id_cpt=None,
    stroke: Stroke | None = None,
    distance=None,
    gender: Gender | None = None,
    phase: Phase | None = None,
    nationality=None,
    swimmer_name=None,
):
    conds = []
    if id_cpt is not None:
        conds.append(result.c.id_cpt == id_cpt)
    if stroke:
        conds.append(event.c.stroke == stroke.value)
    if distance:
        conds.append(event.c.distance == distance)
    if gender:
        conds.append(result.c.gender == gender.value)
    if phase:
        if phase == Phase.final:
            conds.append(result.c.phase.like("final%"))
        else:
            conds.append(result.c.phase == phase.value)
    if nationality:
        conds.append(swimmer.c.nationality == nationality.upper())
    if swimmer_name:
        conds.append(swimmer.c.full_name.ilike(f"%{swimmer_name}%"))
    return conds


_JOIN = (
    result.join(event, result.c.id_event == event.c.id_event)
    .join(competition, result.c.id_cpt == competition.c.id_cpt)
    .join(swimmer, result.c.iuf == swimmer.c.iuf, isouter=True)
    .join(club, result.c.id_club == club.c.id_club, isouter=True)
)

_COLUMNS = [
    result.c.id_cpt,
    competition.c.name.label("competition"),
    competition.c.pool_size,
    event.c.label.label("event"),
    event.c.distance,
    event.c.stroke,
    result.c.gender,
    result.c.phase,
    result.c.race_date,
    result.c.rank,
    result.c.time_cs,
    result.c.reaction,
    result.c.points,
    result.c.iuf,
    swimmer.c.full_name.label("swimmer"),
    swimmer.c.birth_year,
    swimmer.c.nationality,
    club.c.name.label("club"),
]


def _format_time(cs) -> str | None:
    if cs is None:
        return None
    cs = int(cs)
    m, rem = divmod(cs, 6000)
    s, c = divmod(rem, 100)
    return f"{m}:{s:02d}.{c:02d}" if m else f"{s}.{c:02d}"


def results_select(conds, limit: int, offset: int):
    stmt = (
        select(*_COLUMNS).select_from(_JOIN).where(*conds).limit(limit).offset(offset)
    )
    return stmt


def count_select(conds):
    return select(func.count()).select_from(_JOIN).where(*conds)


def row_to_result(row) -> dict:
    d = dict(row._mapping)
    d["time"] = _format_time(d.get("time_cs"))
    if d.get("reaction") is not None:
        d["reaction"] = float(d["reaction"])
    if d.get("race_date") is not None:
        d["race_date"] = str(d["race_date"])
    return d
