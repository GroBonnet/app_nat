from __future__ import annotations

from fastapi import Query

from src.domain.models import Gender, Phase, Stroke


# ----------------------------- Filters for list competitions -----------------------------
def get_competition_list_filters(
    year: int | None = Query(None, description="Année civile"),
    level: str | None = Query(None, description="internationale / nationale"),
    category: str | None = Query(None, description="senior / junior..."),
    pool_size: int | None = Query(None, description="25 ou 50"),
    competition_name: str | None = Query(None, description="Recherche dans le nom"),
) -> dict:
    return {
        "year": year,
        "level": level,
        "category": category,
        "pool_size": pool_size,
        "competition_name": competition_name,
    }


# ----------------------------- Filters for competition/{id_cpt}/results -----------------------------
def get_competition_result_filters(
    stroke: Stroke | None = Query(None, description="Discipline / nage"),
    distance: int | None = Query(
        None, description="Distance en mètres (50, 100, 200...)"
    ),
    gender: Gender | None = Query(None, description="M, F ou X (mixte)"),
    phase: Phase | None = Query(
        None, description="series = qualif, semi = demies, final = finales"
    ),
    nationality: str | None = Query(
        None, description="Code pays du nageur (FRA, AUS...)"
    ),
    swimmer_name: str | None = Query(
        None, description="Recherche dans le nom du nageur"
    ),
) -> dict:
    return {
        "stroke": stroke,
        "distance": distance,
        "gender": gender,
        "phase": phase,
        "nationality": nationality,
        "swimmer_name": swimmer_name,
    }


def get_competition_result_sorting(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    return {
        "limit": limit,
        "offset": offset,
    }
