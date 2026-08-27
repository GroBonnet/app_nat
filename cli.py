from __future__ import annotations

import logging
import sys

from sqlalchemy import func, select, URL

from src.infrastructure.config import get_url
from src.infrastructure.database import drop_schema, ensure_database, init_schema, make_engine
from src.infrastructure.ingest import ingest_dir
from src.domain.schema import club, competition, event, result, swimmer


def _counts(conn) -> dict:
    tables = {"competition": competition, "swimmer": swimmer,
              "result": result, "event": event, "club": club}
    return {name: conn.execute(select(func.count()).select_from(t)).scalar()
            for name, t in tables.items()}


def cmd_create(url: URL) -> None:
    ensure_database(url)
    init_schema(make_engine(url))
    print(f"Base prête ({url.render_as_string(hide_password=True)}).")


def cmd_reset(url: URL) -> None:
    ensure_database(url)
    engine = make_engine(url)
    drop_schema(engine)
    init_schema(engine)
    print("Base réinitialisée.")


def cmd_load(url: URL, load_dir: str) -> None:
    engine = make_engine(url)
    with engine.connect() as conn:
        total = ingest_dir(conn, load_dir)
        counts = _counts(conn)
    print(f"\n{total} résultats chargés.")
    print("  compétitions={competition}  nageurs={swimmer}  résultats={result}"
          "  épreuves={event}  clubs={club}".format(**counts))


def main(
        command: str, 
        url: URL | None = None, 
        verbose: bool = False, 
        load_dir: str = "data/json_results/json"
) -> int:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    url = get_url(url)
    
    commands = {"create": cmd_create, "reset": cmd_reset, "load": cmd_load}
    if command not in commands:
        raise ValueError(f"Commande inconnue: {command!r} (attendu: {', '.join(commands)})")

    if command == "load":
        cmd_load(url, load_dir)
    else:
        commands[command](url)
    return 0


if __name__ == "__main__":
    sys.exit(main(command="load"))
