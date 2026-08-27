from __future__ import annotations

import json
from pathlib import Path

from src.scrapping.normalize import centiseconds_to_str


def flatten_result(comp: dict, r: dict) -> dict:
    """Transforme un résultat + le contexte compétition en une ligne plate."""
    ev = r.get("event", {})
    return {
        # compétition
        "id_cpt": comp.get("id_cpt"),
        "competition": comp.get("name"),
        "cpt_city": comp.get("city"),
        "cpt_country": comp.get("country"),
        "cpt_date_start": comp.get("date_start"),
        "cpt_date_end": comp.get("date_end"),
        "pool_size": comp.get("pool_size"),
        # épreuve
        "event": ev.get("label"),
        "distance": ev.get("distance"),
        "stroke": ev.get("stroke"),
        "is_relay": r.get("is_relay"),
        "gender": r.get("gender"),
        "phase": r.get("phase"),
        "date": r.get("date"),
        # performance
        "rank": r.get("rank"),
        "time_cs": r.get("time_cs"),
        "time": centiseconds_to_str(r.get("time_cs")),
        "reaction": r.get("reaction"),
        "points": r.get("points"),
        # nageur
        "iuf": r.get("iuf"),
        "id_result": r.get("id_result"),
        "swimmer": r.get("full_name"),
        "last_name": r.get("last_name"),
        "first_name": r.get("first_name"),
        "birth_year": r.get("birth_year"),
        "nationality": r.get("nationality"),
        "id_club": r.get("id_club"),
        "club": r.get("club_name"),
    }


def competition_document(data: dict) -> dict:
    """Document JSON imbriqué d'une compétition (méta + résultats enrichis)."""
    comp = data["competition"]
    rows = []
    for r in data["results"]:
        ev = r.get("event", {})
        rows.append(
            {
                "event": ev.get("label"),
                "distance": ev.get("distance"),
                "stroke": ev.get("stroke"),
                "is_relay": r.get("is_relay"),
                "gender": r.get("gender"),
                "phase": r.get("phase"),
                "date": r.get("date"),
                "rank": r.get("rank"),
                "time_cs": r.get("time_cs"),
                "time": centiseconds_to_str(r.get("time_cs")),
                "reaction": r.get("reaction"),
                "points": r.get("points"),
                "iuf": r.get("iuf"),
                "id_result": r.get("id_result"),
                "swimmer": r.get("full_name"),
                "birth_year": r.get("birth_year"),
                "nationality": r.get("nationality"),
                "id_club": r.get("id_club"),
                "club": r.get("club_name"),
            }
        )
    return {**comp, "results": rows}


def write_competition_json(data: dict, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"cpt_{data['competition']['id_cpt']}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(competition_document(data), fh, ensure_ascii=False, indent=2)
    return path


def append_jsonl(data: dict, path: str | Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    comp = data["competition"]
    n = 0
    with path.open("a", encoding="utf-8") as fh:
        for r in data["results"]:
            fh.write(json.dumps(flatten_result(comp, r), ensure_ascii=False) + "\n")
            n += 1
    return n
