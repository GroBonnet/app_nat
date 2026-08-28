from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests

BASE = "https://ffn.extranat.fr/webffn/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "ffn-stats/0.1 (projet personnel de visualisation de résultats ; "
        "contact: modifier-cet-email@example.com)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


class Client:
    def __init__(
        self,
        cache_dir: str | Path = "data/cache",
        min_delay: float = 1.5,
        timeout: int = 30,
        max_retries: int = 3,
        use_cache: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_delay = min_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_cache = use_cache
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _cache_path(self, url: str) -> Path:
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{h}.html"

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request = time.time()

    def get(
        self, path_or_url: str, params: dict | None = None, force: bool = False
    ) -> str:
        url = path_or_url if path_or_url.startswith("http") else BASE + path_or_url
        if params:
            req = requests.Request("GET", url, params=params).prepare()
            url = req.url

        cache_file = self._cache_path(url)
        if self.use_cache and not force and cache_file.exists():
            return cache_file.read_text(encoding="utf-8", errors="replace")

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                # ExtraNat sert de l'ISO-8859-1 mal déclaré parfois.
                if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                html = resp.text
                if self.use_cache:
                    cache_file.write_text(html, encoding="utf-8", errors="replace")
                return html
            except Exception as exc:
                last_exc = exc
                wait = self.min_delay * (2**attempt)
                time.sleep(wait)
        raise RuntimeError(
            f"Échec du téléchargement après {self.max_retries} essais : {url}"
        ) from last_exc
