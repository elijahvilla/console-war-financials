"""Polite SEC EDGAR client: identifies itself (User-Agent from env), throttles, retries, caches on disk.

The User-Agent is a contact the SEC requires. It is read from SEC_USER_AGENT (.env) and is never printed,
logged, or written to the cache: cache files hold only response bodies, keyed by sha256(url).
"""
import hashlib
import json
import os
import time
from pathlib import Path

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class ConfigError(Exception):
    pass


class SecError(Exception):
    pass


def _cache_path(cache_dir: Path, url: str) -> Path:
    return Path(cache_dir) / hashlib.sha256(url.encode("utf-8")).hexdigest()


def cached_get(url: str, cache_dir: Path = Path("data/cache"), session=None, offline: bool = False) -> bytes:
    """Plain cached GET for non-SEC sources (FRED needs no contact header)."""
    path = _cache_path(cache_dir, url)
    if path.exists():
        return path.read_bytes()
    if offline:
        raise SecError(f"offline and not cached: {url}")
    r = (session or requests).get(url, timeout=60)
    if r.status_code != 200:
        raise SecError(f"HTTP {r.status_code} for {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content


class SecClient:
    def __init__(self, user_agent: str | None = None, cache_dir: Path = Path("data/cache"),
                 min_interval: float = 0.2, session=None, clock=time.monotonic, sleep=time.sleep,
                 load_env: bool = True, offline: bool = False):
        if user_agent is None:
            if load_env:
                from dotenv import load_dotenv
                load_dotenv()
            user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
        if not user_agent and not offline:
            raise ConfigError("set SEC_USER_AGENT in .env")
        self._headers = {"User-Agent": user_agent or "", "Accept-Encoding": "gzip, deflate"}
        self.cache_dir = Path(cache_dir)
        self.min_interval = min_interval
        self.session = session or requests.Session()
        self._clock, self._sleep = clock, sleep
        self._last = None
        self.offline = offline
        self.network_calls = 0

    def __repr__(self):  # never show the contact string
        return f"SecClient(cache_dir={self.cache_dir!s}, offline={self.offline})"

    def _throttle(self):
        if self._last is not None:
            wait = self.min_interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()

    def get(self, url: str) -> bytes:
        path = _cache_path(self.cache_dir, url)
        if path.exists():
            return path.read_bytes()
        if self.offline:
            raise SecError(f"offline and not cached: {url}")
        for attempt in range(MAX_RETRIES + 1):
            self._throttle()
            self.network_calls += 1
            r = self.session.get(url, headers=self._headers, timeout=120)
            if r.status_code == 200:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(r.content)
                return r.content
            if r.status_code not in RETRY_STATUS or attempt == MAX_RETRIES:
                raise SecError(f"HTTP {r.status_code} for {url}")
            self._sleep(2 ** attempt)
        raise SecError(f"unreachable: {url}")

    def get_json(self, url: str) -> dict:
        return json.loads(self.get(url))
