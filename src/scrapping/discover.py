from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

PARSER = "html.parser"

# Codes du filtre "Type de compétition" (idtyp) relevés sur le site.
TYPE_CODES = {
    "internationales": 7,
    "championnats_nationaux": 6,
    "meetings_nationaux": 5,
    "coupes_nationales": 14,
    "interregionales": 8,
    "regionaux_web": 12,
    "championnats_regionaux": 4,
    "coupes_regionales": 15,
    "interclubs_tc": 3,
    "interclubs_jeunes": 2,
    "interclubs_avenirs": 1,
    "animation": 13,
}

_DATE_TOKEN_RE = re.compile(r"\b(\d{2})/(\d{2})(?:/(\d{2,4}))?\b")
_CITY_RE = re.compile(r"([A-ZÀ-Ý][A-ZÀ-Ý' \-]{2,})\s*\(([A-Z]{2,3})\)")


def _extract_range(text: str) -> tuple[str | None, str | None]:
    """Renvoie (date_début, date_fin) ISO depuis un texte de type
    'Me 30/07 - Ve 01/08/25 | Mercredi 30/07 - Vendredi 01/08/2025'.

    L'année n'est portée que par la date de fin : on la reporte sur le début,
    en gérant le passage d'année (décembre -> janvier).
    """
    toks = _DATE_TOKEN_RE.findall(text)
    if not toks:
        return None, None
    years = [int(y) if len(y) == 4 else 2000 + int(y) for _d, _m, y in toks if y]
    base = max(years) if years else None
    if base is None:
        return None, None
    pairs = sorted({(int(m), int(d)) for d, m, _y in toks})  # (mois, jour)
    (sm, sd), (em, ed) = pairs[0], pairs[-1]
    start_year = end_year = base
    if sm > em:  # ex. décembre -> janvier : le début est l'année précédente
        start_year = base - 1
    return f"{start_year:04d}-{sm:02d}-{sd:02d}", f"{end_year:04d}-{em:02d}-{ed:02d}"


_CATEGORY_PATTERNS = [
    ("Master", re.compile(r"ma[îi]tres?|masters?", re.I)),
    ("Universitaire", re.compile(r"universitaires?|universiade", re.I)),
    ("U23", re.compile(r"\bu23?\b", re.I)),
    ("Junior", re.compile(r"\bjuniors?\b", re.I)),
    ("Cadet", re.compile(r"\bcadet(te)?s?\b", re.I)),
    ("Minime", re.compile(r"\bminimes?\b", re.I)),
    ("Benjamin", re.compile(r"\bbenjamin(e)?s?\b", re.I)),
    ("Avenir", re.compile(r"\bavenirs?\b", re.I)),
    ("Jeune", re.compile(r"\bjeunes?\b|jeunesse", re.I)),
    ("Senior", re.compile(r"\bs[ée]niors?\b", re.I)),
]


def detect_category(*texts: str) -> str:
    """Déduit la/les catégorie(s) d'âge d'une compétition depuis son nom/type.

    Renvoie une chaîne ("Juniors", "Juniors, Seniors", "Maîtres"...) ou None
    quand aucun marqueur n'est présent (cas des meets « open » / seniors, où
    l'absence de mention = pas de restriction d'âge, ex. Championnats du Monde).

    >>> detect_category("Championnats d'Europe Juniors")
    'Juniors'
    >>> detect_category("Meeting", "Type de compétition : Championnats Régionaux Juniors & Séniors")
    'Juniors, Seniors'
    >>> detect_category("Championnats du Monde en grand bassin") is None
    True
    """
    blob = " ".join(t for t in texts if t)
    found = [label for label, pat in _CATEGORY_PATTERNS if pat.search(blob)]
    # dédoublonnage en gardant l'ordre
    seen, ordered = set(), []
    for lab in found:
        if lab not in seen:
            seen.add(lab)
            ordered.append(lab)
    return ", ".join(ordered) if ordered else "Senior"


# "Type de compétition : <libellé> (<code>)"  -> libellé + code
_TYPE_RE = re.compile(r"Type de compétition\s*:\s*(.+?)\s*(?:\((\d+)\))?\s*$")
# Niveau (catégorie large) : "International Int.", "National Nat."...
_LEVEL_RE = re.compile(
    r"\b(International|Interrégional|National|Régional|Départemental)\s+"
    r"(?:Int|Interrég|Nat|Rég|Dép)\."
)


def build_list_url(season_end_year: int, month: int | None = None,
                   idtyp: int | str | None = None, idreg: str = "", iddep: str = "") -> str:
    """Construit l'URL de la liste filtrée."""
    if isinstance(idtyp, str) and idtyp:
        idtyp = TYPE_CODES.get(idtyp, idtyp)
    parts = ["idact=nat", f"idsai={season_end_year}"]
    if month:
        parts.append(f"idmth={month}")
    if idtyp not in (None, "", 0):        # aucun type -> toutes les compétitions
        parts.append(f"idtyp={idtyp}")
    parts.append(f"idreg={idreg}")
    parts.append(f"iddep={iddep}")
    return "competitions.php?" + "&".join(parts)


def _idcpt(href: str) -> int | None:
    v = parse_qs(urlparse(href).query).get("idcpt", [None])[0]
    return int(v) if v and v.isdigit() else None


def _is_comp_link(href: str | None) -> bool:
    return bool(href) and "resultats.php" in href and "idcpt=" in href and "go=res" not in href


def parse_competition_list(html: str) -> list[dict]:
    """Extrait la liste des compétitions d'une page liste ExtraNat."""
    soup = BeautifulSoup(html, PARSER)
    found: dict[int, dict] = {}

    for a in soup.find_all("a", href=_is_comp_link):
        id_cpt = _idcpt(a.get("href", ""))
        if id_cpt is None:
            continue
        name = a.get_text(" ", strip=True)
        block = a.find_parent("div", class_="border-b") or a.find_parent(["li", "div"]) or a.parent
        text = block.get_text(" ", strip=True) if block else name

        date_start, date_end = _extract_range(text)

        city = country = None
        cm = _CITY_RE.search(text)
        if cm:
            city, country = cm.group(1).strip().title(), cm.group(2)

        # Type de compétition officiel (libellé + code numérique FFN).
        comp_type = type_code = None
        tm = _TYPE_RE.search(text)
        if tm:
            comp_type = tm.group(1).strip()
            type_code = int(tm.group(2)) if tm.group(2) else None

        # Niveau (catégorie large) : International / National / Régional...
        level = None
        lm = _LEVEL_RE.search(text)
        if lm:
            level = lm.group(1)

        category = detect_category(name, comp_type or "")
        
        prev = found.get(id_cpt)
        if prev is None or len(name) > len(prev["name"]):
            found[id_cpt] = {
                "id_cpt": id_cpt, "name": name,
                "date_start": date_start, "date_end": date_end,
                "city": city, "country": country,
                "level": level, "type": comp_type, "type_code": type_code,
                "category": category,
            }

    return sorted(found.values(), key=lambda c: (c["date_start"] or "9999", c["id_cpt"]))


def discover(season_end_year: int, month: int | None, client, idtyp: int | str | None = None) -> list[dict]:
    """Télécharge la liste filtrée et renvoie les compétitions."""
    url = build_list_url(season_end_year, month, idtyp)
    html = client.get(url)
    return parse_competition_list(html)


def discover_from_file(path: str) -> list[dict]:
    """Extrait les compétitions d'un fichier HTML de liste sauvegardé."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_competition_list(fh.read())


_MAJOR_RE = re.compile(
    r"championnats?\s+d[u']?\s*(monde|europe)|jeux\s+olympiques|olympic", re.I
)


def is_major_senior(comp: dict) -> bool:
    """True si la compétition est des Championnats du Monde / d'Europe / JO
    en catégorie SENIOR.

    Le petit et le grand bassin sont tous deux acceptés (le nom contient
    « petit/grand bassin »). Les versions non-seniors sont exclues via le
    champ `category` : Juniors, Jeunesse, Maîtres, Universitaire...
    """
    text = f"{comp.get('name', '')} {comp.get('type', '')}"
    if not _MAJOR_RE.search(text):
        return False
    return comp["category"] == "Senior"


def select_major_senior(comps: list[dict]) -> list[dict]:
    """Ne conserve que les grands championnats seniors (Monde/Europe/JO)."""
    return [c for c in comps if is_major_senior(c)]