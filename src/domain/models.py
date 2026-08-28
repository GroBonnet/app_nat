from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


# --- Énumérations de filtres ----------------------------------------------
class Stroke(StrEnum):
    NL = "NL"  # nage libre
    DOS = "DOS"
    BRA = "BRA"  # brasse
    PAP = "PAP"  # papillon
    MEDLEY = "4N"  # 4 nages


class Gender(StrEnum):
    M = "M"
    F = "F"
    X = "X"  # mixte (relais)


class Phase(StrEnum):
    series = "series"  # séries / qualifications
    semi = "semi"  # demi-finales
    final = "final"  # finales (A/B/C)


# --- Modèles de réponse ----------------------------------------------------
class Competition(BaseModel):
    id_cpt: int
    name: str | None = None
    city: str | None = None
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    pool_size: int | None = None
    level: str | None = None
    type: str | None = None
    category: str | None = None
    season: str | None = None
    n_results: int | None = None


class Result(BaseModel):
    id_cpt: int
    competition: str | None = None
    pool_size: int | None = None
    event: str | None = None
    distance: int | None = None
    stroke: str | None = None
    gender: str | None = None
    phase: str | None = None
    race_date: str | None = None
    rank: int | None = None
    time_cs: int | None = None
    time: str | None = None
    reaction: float | None = None
    points: int | None = None
    iuf: int | None = None
    swimmer: str | None = None
    birth_year: int | None = None
    nationality: str | None = None
    club: str | None = None


class ResultsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Result]
