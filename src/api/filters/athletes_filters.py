from fastapi import Query

from src.domain.models import Stroke


# ----------------------------- Filters for atletes best time -----------------------------
def get_athlete_best_times_filters(
    stroke: Stroke | None = Query(None, description="Filtrer sur une nage"),
    pool_size: int | None = Query(None, description="25 ou 50"),
    include_relays: bool = Query(
        False, description="Inclure les temps de relais (par défaut : non)"
    ),
) -> dict:
    return {"stroke": stroke, "pool_size": pool_size, "include_relays": include_relays}
