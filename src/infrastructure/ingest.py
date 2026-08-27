from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path

from src.infrastructure.repository import (
    delete_results_for,
    insert_results,
    upsert_clubs,
    upsert_competitions,
    upsert_events,
    upsert_swimmers,
)

log = logging.getLogger("pg.ingest")


# --- transformations -------------------------------------------------------
def split_name(full: str | None) -> tuple[str | None, str | None]:
    """'HARRIS Meg' -> ('HARRIS', 'Meg') (mots MAJUSCULES = nom)."""
    if not full:
        return None, None
    last, first = [], []
    for tok in full.split():
        letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", tok)
        if letters and letters == letters.upper() and not first:
            last.append(tok)
        else:
            first.append(tok)
    if not last:
        toks = full.split()
        last, first = toks[:1], toks[1:]
    return " ".join(last) or None, " ".join(first) or None


def parse_reaction(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ".").lstrip("+"))
    except ValueError:
        return None


def _date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _dt(s) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except ValueError:
        return None


# --- chargement ------------------------------------------------------------
def ingest_file(conn, path: str | Path) -> int:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    id_cpt = doc.get("id_cpt")
    if id_cpt is None:
        log.warning("Fichier sans id_cpt ignoré : %s", path)
        return 0

    comp_row = {
        "id_cpt": id_cpt,
        "name": doc.get("name"),
        "city": doc.get("city"),
        "country": doc.get("country"),
        "date_start": _date(doc.get("date_start")),
        "date_end": _date(doc.get("date_end")),
        "pool_size": doc.get("pool_size"),
        "level": doc.get("level"),
        "type": doc.get("type"),
        "type_code": doc.get("type_code"),
        "category": doc.get("category"),
        "season": doc.get("season"),
        "scraped_at": _dt(doc.get("scraped_at")),
    }

    clubs: dict[int, dict] = {}
    swimmers: dict[int, dict] = {}
    events: dict[tuple, dict] = {}
    staged: list[dict] = []

    for r in doc.get("results", []):
        distance, stroke = r.get("distance"), r.get("stroke")
        if distance is None or stroke is None:
            continue
        is_relay = bool(r.get("is_relay"))
        ev_key = (distance, stroke, is_relay)
        events.setdefault(
            ev_key,
            {
                "distance": distance,
                "stroke": stroke,
                "is_relay": is_relay,
                "label": r.get("event"),
            },
        )

        iuf = r.get("iuf")
        if iuf is not None:
            last, first = split_name(r.get("swimmer"))
            swimmers[iuf] = {
                "iuf": iuf,
                "last_name": last,
                "first_name": first,
                "full_name": r.get("swimmer"),
                "birth_year": r.get("birth_year"),
                "nationality": r.get("nationality"),
                "gender": r.get("gender"),
            }

        id_club = r.get("id_club")
        if id_club is not None:
            clubs[id_club] = {"id_club": id_club, "name": r.get("club")}

        staged.append(
            {
                "ev_key": ev_key,
                "iuf": iuf,
                "id_club": id_club,
                "id_res": r.get("id_result"),
                "rank": r.get("rank"),
                "time_cs": r.get("time_cs"),
                "reaction": parse_reaction(r.get("reaction")),
                "points": r.get("points"),
                "phase": r.get("phase"),
                "gender": r.get("gender"),
                "race_date": _date(r.get("date")),
                "is_relay": is_relay,
            }
        )

    with conn.begin():  # transaction par compétition
        upsert_competitions(conn, [comp_row])
        upsert_clubs(conn, list(clubs.values()))
        upsert_swimmers(conn, list(swimmers.values()))
        event_map = upsert_events(conn, list(events.values()))
        delete_results_for(conn, [id_cpt])
        rows = [
            {
                "id_cpt": id_cpt,
                "id_event": event_map[s["ev_key"]],
                "iuf": s["iuf"],
                "id_club": s["id_club"],
                "id_res": s["id_res"],
                "rank": s["rank"],
                "time_cs": s["time_cs"],
                "reaction": s["reaction"],
                "points": s["points"],
                "phase": s["phase"],
                "gender": s["gender"],
                "race_date": s["race_date"],
                "is_relay": s["is_relay"],
            }
            for s in staged
        ]
        insert_results(conn, rows)

    log.info(
        "cpt %s : %d résultats chargés (%s)", id_cpt, len(staged), doc.get("name") or ""
    )
    return len(staged)


def ingest_dir(conn, json_dir: str | Path) -> int:
    files = sorted(Path(json_dir).glob("cpt_*.json"))
    if not files:
        log.warning("Aucun fichier cpt_*.json dans %s", json_dir)
    total = 0
    for f in files:
        try:
            total += ingest_file(conn, f)
        except Exception:
            log.exception("Échec sur %s", f)
    return total
