import json
from functools import lru_cache
from pathlib import Path

WR_DIR = Path(__file__).parents[2] / "data" / "world_records"

_FILES = {
    (50, "M"): "men_50.json",
    (50, "F"): "women_50.json",
    (25, "M"): "men_25.json",
    (25, "F"): "women_25.json",
}


@lru_cache
def _load(pool_size: int, gender: str) -> dict[tuple[str, int], dict]:
    payload = json.loads(
        (WR_DIR / _FILES[(pool_size, gender)]).read_text(encoding="utf-8")
    )
    return {(r["stroke"], r["distance"]): r for r in payload["records"]}


def get_world_record(
    stroke: str, distance: int, pool_size: int, gender: str
) -> dict | None:
    return _load(pool_size, gender).get((stroke, distance))
