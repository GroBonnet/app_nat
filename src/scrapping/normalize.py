from __future__ import annotations

import re

# --- Temps -----------------------------------------------------------------

# Formats rencontrés : "SS.CC", "MM:SS.CC", "HH:MM:SS.CC"
_TIME_RE = re.compile(r"^\s*(?:(?:(\d{1,2}):)?(\d{1,2}):)?(\d{1,2})[.,](\d{2})\s*$")


def time_to_centiseconds(raw: str) -> int | None:
    """Convertit un temps FFN en centièmes de seconde.

    >>> time_to_centiseconds("00:30.66")
    3066
    >>> time_to_centiseconds("01:23.79")
    8379
    >>> time_to_centiseconds("27.89")
    2789
    >>> time_to_centiseconds("1:02:15.40")
    373540
    """
    if not raw:
        return None
    m = _TIME_RE.match(raw)
    if not m:
        return None
    hours, minutes, seconds, cents = m.groups()
    h = int(hours) if hours else 0
    mnt = int(minutes) if minutes else 0
    total = ((h * 60 + mnt) * 60 + int(seconds)) * 100 + int(cents)
    return total


def centiseconds_to_str(cs: int | None) -> str:
    """Formatte des centièmes en chaîne lisible (MM:SS.CC ou SS.CC)."""
    if cs is None:
        return ""
    minutes, rem = divmod(cs, 6000)
    seconds, cents = divmod(rem, 100)
    if minutes:
        return f"{minutes:d}:{seconds:02d}.{cents:02d}"
    return f"{seconds:d}.{cents:02d}"


# --- Épreuves --------------------------------------------------------------

# Nage libre / Dos / Brasse / Papillon / 4 Nages, avec variantes d'orthographe.
_STROKE_PATTERNS = [
    ("NL", re.compile(r"nage\s*libre|\bnl\b|\blibre\b|freestyle", re.I)),
    ("4N", re.compile(r"4\s*nages|quatre\s*nages|medley", re.I)),
    ("DOS", re.compile(r"\bdos\b|backstroke", re.I)),
    ("BRA", re.compile(r"brasse|breaststroke", re.I)),
    ("PAP", re.compile(r"papillon|\bpap\b|butterfly", re.I)),
]

_STROKE_LABELS = {
    "NL": "Nage Libre",
    "DOS": "Dos",
    "BRA": "Brasse",
    "PAP": "Papillon",
    "4N": "4 Nages",
}

_DISTANCE_RE = re.compile(r"(\d{2,4})\s*m?\b")


def parse_gender(text: str) -> str | None:
    """'Dames' -> 'F', 'Messieurs' -> 'M', 'Mixte' -> 'X'."""
    low = (text or "").lower()
    if "mixte" in low:
        return "X"
    if "dames" in low or "femmes" in low:
        return "F"
    if "messieurs" in low or "hommes" in low:
        return "M"
    return None


def parse_phase(text: str) -> str | None:
    """Normalise la manche : séries / demi-finale / finale A|B|C.

    >>> parse_phase("50 Nage Libre Dames - Finale A")
    'final_a'
    >>> parse_phase("... - 1/2 Finale (1)")
    'semi'
    >>> parse_phase("... - Séries")
    'series'
    """
    low = (text or "").lower()
    if "1/2" in low or "demi" in low or "1/2 finale" in low:
        return "semi"
    if "finale" in low or "final" in low:
        m = re.search(r"finale?\s*([abc])\b", low)
        if m:
            return f"final_{m.group(1)}"
        return "final"
    if "série" in low or "series" in low or "serie" in low:
        return "series"
    if "classement" in low:
        return "classement"
    return None


def parse_event_title(title: str) -> dict | None:
    """Extrait distance, nage, relais, sexe et manche d'un libellé d'épreuve.

    Renvoie None si le texte n'est pas une épreuve (pas de distance+nage).

    >>> e = parse_event_title("50 Nage Libre Dames - Finale A")
    >>> (e['distance'], e['stroke'], e['gender'], e['phase'], e['label'])
    (50, 'NL', 'F', 'final_a', '50m Nage Libre')
    >>> parse_event_title("4x100 4 Nages Messieurs - Séries")['is_relay']
    True
    >>> parse_event_title("Classement des 1/2 Finales") is None
    True
    """
    if not title:
        return None
    text = title.strip()

    is_relay = bool(re.search(r"\b\d\s*x\s*\d", text, re.I)) or "relais" in text.lower()

    relay_m = re.search(r"(\d)\s*x\s*(\d{2,4})", text, re.I)
    if relay_m:
        distance = int(relay_m.group(1)) * int(relay_m.group(2))
    else:
        dm = _DISTANCE_RE.search(text)
        if not dm:
            return None
        distance = int(dm.group(1))

    stroke = None
    for code, pat in _STROKE_PATTERNS:
        if pat.search(text):
            stroke = code
            break
    if stroke is None:
        return None

    label = f"{distance}m {_STROKE_LABELS[stroke]}"
    if is_relay:
        label = "Relais " + label
    return {
        "distance": distance,
        "stroke": stroke,
        "is_relay": is_relay,
        "gender": parse_gender(text),
        "phase": parse_phase(text),
        "label": label,
    }


def stroke_label(code: str) -> str:
    return _STROKE_LABELS.get(code, code)


_FR_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}


def parse_fr_date(text: str) -> str | None:
    """'Dimanche 3 Août 2025' -> '2025-08-03' (ISO). None si absent."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})", text)
    if not m:
        return None
    mon = _FR_MONTHS.get(m.group(2).lower())
    if not mon:
        return None
    return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"


# --- Divers ----------------------------------------------------------------

def parse_birth_year(text: str) -> int | None:
    """Récupère l'année de naissance dans un fragment type "(2011/15 ans)"."""
    m = re.search(r"(19|20)\d{2}", text or "")
    return int(m.group(0)) if m else None
