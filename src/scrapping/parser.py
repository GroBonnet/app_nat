from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from src.scrapping.normalize import (parse_birth_year, parse_event_title, parse_fr_date,
                        time_to_centiseconds)

_TIME_RE = re.compile(r"^(?:\d{1,2}:){0,2}\d{1,2}[.,]\d{2}$")
_POINTS_RE = re.compile(r"(\d{1,4})\s*pts", re.I)
_REACT_RE = re.compile(r"^[+\-]\d[.,]\d{2}$")
_RANK_RE = re.compile(r"^(\d{1,3})\.?$")
_NAT_RE = re.compile(r"\)\s*([A-Z]{3})\s*$")  # nationalité en fin : "(2002/23 ans) AUS"

PARSER = "html.parser"  # gère mieux les tables imbriquées d'ExtraNat que lxml


def _qp(href: str, key: str) -> str | None:
    try:
        return parse_qs(urlparse(href).query).get(key, [None])[0]
    except Exception:  # noqa: BLE001
        return None


def _anchor(href: str) -> str | None:
    frag = urlparse(href).fragment
    return frag or None


def _split_name(full: str) -> tuple[str, str]:
    tokens = full.split()
    last, first = [], []
    for tok in tokens:
        letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", tok)
        if letters and letters == letters.upper() and not first:
            last.append(tok)
        else:
            first.append(tok)
    if not last:
        last, first = tokens[:1], tokens[1:]
    return " ".join(last), " ".join(first)


# --- Métadonnées de compétition -------------------------------------------
def parse_competition_meta(html: str) -> dict:
    """Récupère les metadata d'une compétition"""
    soup = BeautifulSoup(html, PARSER)
    name = city = country = None

    _LOC_RE = re.compile(r"(.*?)\s*-\s*([A-ZÀ-Ý][^()]+?)\s*\(([A-Z]{2,3})\)\s*$")
    _SKIP = {"légende", "legende", "espace ressources", "partenaires",
             "sites complémentaires", "contact", "consulter vos résultats"}

    headings = soup.find_all(["h1", "h2", "h3"])
    title_tag = None
    # 1) titre "Nom - VILLE (PAYS)"
    for h in headings:
        if _LOC_RE.match(h.get_text(" ", strip=True)):
            title_tag = h
            break
    # 2) sinon, l'en-tête mis en avant (text-lg font-bold)
    if title_tag is None:
        for h in headings:
            cls = " ".join(h.get("class") or [])
            if "text-lg" in cls and "font-bold" in cls:
                title_tag = h
                break
    # 3) sinon, le premier en-tête « utile »
    if title_tag is None:
        for h in headings:
            t = h.get_text(" ", strip=True)
            if t and t.lower() not in _SKIP:
                title_tag = h
                break

    if title_tag is not None:
        raw = title_tag.get_text(" ", strip=True)
        m = _LOC_RE.match(raw)
        if m:
            name, city, country = m.group(1).strip(), m.group(2).strip().title(), m.group(3)
        else:
            name = raw

    text = soup.get_text(" ", strip=True)
    pool_size = None
    if re.search(r"grand\s*bassin", text, re.I):
        pool_size = 50
    elif re.search(r"petit\s*bassin", text, re.I):
        pool_size = 25
    else:
        pm = re.search(r"bassin\s*(?:de)?\s*(\d{2})\s*m", text, re.I)
        if pm:
            pool_size = int(pm.group(1))

    return {"name": name, "city": city, "country": country, "pool_size": pool_size}


# --- Liste des URL d'épreuves ---------------------------------------------
def parse_event_urls(html: str, base_url: str | None = None) -> list[str]:
    """Récupère les urls de chaque épreuve d'une compétition."""
    soup = BeautifulSoup(html, PARSER)
    urls: list[str] = []
    seen: set[str] = set()
    for sel in soup.find_all("select"):
        name = sel.get("name") or ""
        if not name.startswith("idepr"):
            continue
        for opt in sel.find_all("option"):
            val = (opt.get("value") or "").strip()
            if "go=epr" in val and "idepr=" in val:
                url = urljoin(base_url or "", val) if base_url else val
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    return urls


# --- Résultats d'une page d'épreuve ---------------------------------------
def _parse_row(tds, event: dict, phase: str | None, date_iso: str | None, gender: str | None) -> dict | None:
    cells = [td.get_text(" ", strip=True) for td in tds]

    # nageur : la cellule qui contient un lien idres
    swim_a = None
    club_a = None
    for td in tds:
        for a in td.find_all("a", href=True):
            href = a["href"]
            if "idres=" in href and swim_a is None:
                swim_a = a
            elif "idban=" in href and "idres=" not in href and club_a is None:
                club_a = a

    rank = None
    for c in cells:
        m = _RANK_RE.match(c)
        if m:
            rank = int(m.group(1))
            break

    time_cs = None
    for c in cells:
        if _TIME_RE.match(c):
            time_cs = time_to_centiseconds(c)
            break

    points = None
    for c in cells:
        pm = _POINTS_RE.search(c)
        if pm:
            points = int(pm.group(1))
            break

    reaction = None
    for c in cells:
        if _REACT_RE.match(c):
            reaction = c.replace(",", ".")
            break

    iuf = idres = idban = None
    full_name = last_name = first_name = None
    nationality = birth_year = None
    if swim_a is not None:
        href = swim_a["href"]
        iuf = _anchor(href)
        iuf = int(iuf) if iuf and re.fullmatch(r"-?\d+", iuf) else None
        idres = _qp(href, "idres")
        idban = _qp(href, "idban")
        stext = swim_a.get_text(" ", strip=True)
        nm = _NAT_RE.search(stext)
        if nm:
            nationality = nm.group(1)
        full_name = re.split(r"\s*\(", stext)[0].strip()
        last_name, first_name = _split_name(full_name)
        birth_year = parse_birth_year(stext)

    club_name = club_a.get_text(" ", strip=True) if club_a else None
    id_club = _qp(club_a["href"], "idban") if club_a else None

    is_relay = event["is_relay"]
    if iuf is None and not is_relay and time_cs is None:
        return None  # ligne vide / séparateur

    return {
        "event": {k: event[k] for k in ("distance", "stroke", "is_relay", "label")},
        "gender": event.get("gender") or gender,
        "phase": phase,
        "date": date_iso,
        "rank": rank,
        "iuf": iuf,
        "id_result": int(idres) if idres and idres.isdigit() else None,
        "full_name": full_name,
        "last_name": last_name,
        "first_name": first_name,
        "birth_year": birth_year,
        "nationality": nationality,
        "id_club": int(id_club) if id_club and id_club.isdigit() else None,
        "club_name": club_name,
        "time_cs": time_cs,
        "reaction": reaction,
        "points": points,
        "is_relay": is_relay,
    }


def _rows_after_thead(thead) -> list:
    """Lignes <tr> de données appartenant à ce <thead>, même sans <tbody>."""
    rows = []
    node = thead
    while True:
        node = node.find_next_sibling()
        if node is None:
            break
        name = getattr(node, "name", None)
        if name == "thead":          # manche suivante -> stop
            break
        if name == "tbody":
            rows.extend(node.find_all("tr", recursive=False))
        elif name == "tr":
            rows.append(node)
    return rows


def parse_event_page(html: str) -> list[dict]:
    """Analyse une page d'épreuve : renvoie la liste des résultats (toutes manches)."""
    soup = BeautifulSoup(html, PARSER)
    results: list[dict] = []

    for thead in soup.find_all("thead"):
        cells = [th.get_text(" ", strip=True) for th in thead.find_all(["th", "td"])]
        header_text = cells[0] if cells else thead.get_text(" ", strip=True)
        date_text = cells[1] if len(cells) > 1 else header_text

        event = parse_event_title(header_text)
        if not event:
            continue  # ex. "Classement des 1/2 Finales" : pas une épreuve

        if event["is_relay"]:
            continue

        phase = event["phase"]
        gender = event["gender"]
        date_iso = parse_fr_date(date_text) or parse_fr_date(header_text)

        
        for tr in _rows_after_thead(thead):
            tds = tr.find_all("td", recursive=False) or tr.find_all("td")
            if not tds:
                continue
            row = _parse_row(tds, event, phase, date_iso, gender)
            if row:
                results.append(row)

    return results
