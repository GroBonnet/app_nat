from __future__ import annotations
import logging
import sys
from pathlib import Path

from src.scrapping.client import Client
from src.scrapping.discover import discover, select_major_senior
from src.scrapping.export import append_jsonl, write_competition_json
from src.scrapping.scraper import collect_competition


def build_competition_list(
        season: int,
        month: int | None,
        type: str,
        client: Client,
        major: bool = False
) -> list[dict]:
    if season or type:
        comps = discover(season, month, client, type)
        if major:
            comps = select_major_senior(comps)
        return comps
    raise SystemExit("Indique une source : --season/--month, and a type")


def main(
        season: int,
        month: int | None,
        type: int | str | None,
        output_dir: str,
        cache_dir: str,
        delay: float = 1.5,
        force: bool = False,
        no_cache: bool = False,
        dry_run: bool = False,
        major: bool = False,
        verbose: bool = False
):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    client = Client(cache_dir=cache_dir, min_delay=delay, use_cache=no_cache)

    comps = build_competition_list(season, month, type, client, major)
    print(f"\n{len(comps)} compétition(s) à traiter :")
    for c in comps:
        extra = f" | {c.get('date_start')}→{c.get('date_end')} | {c.get('city') or ''}" if c.get("name") else ""
        print(f"  - {c['id_cpt']} {c.get('name','') }{extra}")
    if dry_run:
        return 0

    out_dir = Path(output_dir)
    json_dir = out_dir / "json"
    jsonl_path = out_dir / "results.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()

    total = 0
    for c in comps:
        try:
            data = collect_competition(c["id_cpt"], client, meta_hint=c, force=force)
        except Exception as exc:
            logging.error("Échec cpt %s : %s", c["id_cpt"], exc)
            continue

        write_competition_json(data, json_dir)
        n = append_jsonl(data, jsonl_path)
        total += n
        print(f"  ✓ {c['id_cpt']} {data['competition'].get('name') or ''} : "
              f"{data['competition']['n_results']} résultats "
              f"({data['competition']['n_events']} épreuves)")

    print(f"\nTerminé : {total} résultats -> {json_dir}/  et  {jsonl_path}")


if __name__ == "__main__":
    sys.exit(main(season=2025, month=None, type=7, output_dir="data/json_results", cache_dir="", dry_run=False, major=True))
