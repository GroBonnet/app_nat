from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.scrapping.client import Client
from src.scrapping.parser import parse_competition_meta, parse_event_page, parse_event_urls

log = logging.getLogger("ffn.scraper")


def collect_competition(id_cpt: int, client: Client, meta_hint: dict | None = None,
                        force: bool = False) -> dict:
    """Scrape une compétition et renvoie {competition, results} (données brutes)."""
    first = client.get("resultats.php",
                       {"idact": "nat", "idcpt": id_cpt, "go": "epr"}, force=force)
    meta = parse_competition_meta(first)
    event_urls = parse_event_urls(first)

    if not event_urls:
        landing = client.get("resultats.php", {"idact": "nat", "idcpt": id_cpt}, force=force)
        meta = parse_competition_meta(landing) or meta
        event_urls = parse_event_urls(landing)

    results: list[dict] = []
    for i, url in enumerate(event_urls, 1):
        log.info("  cpt %s : épreuve %d/%d", id_cpt, i, len(event_urls))
        html = client.get(url, force=force)
        results.extend(parse_event_page(html))

    # fusion des métadonnées : la liste (meta_hint) prime pour nom/dates/ville,
    # la page complète le bassin / pays.
    merged = {
        "id_cpt": id_cpt,
        "name": (meta_hint or {}).get("name") or meta.get("name"),
        "city": (meta_hint or {}).get("city") or meta.get("city"),
        "country": (meta_hint or {}).get("country") or meta.get("country"),
        "pool_size": meta.get("pool_size"),
        "date_start": (meta_hint or {}).get("date_start"),
        "date_end": (meta_hint or {}).get("date_end"),
        "type": (meta_hint or {}).get("type"),
        "n_events": len(event_urls),
        "n_results": len(results),
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    log.info("cpt %s : %d épreuves, %d résultats", id_cpt, len(event_urls), len(results))
    return {"competition": merged, "results": results}
