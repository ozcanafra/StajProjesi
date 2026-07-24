"""Shared HTTP fetch helper for the passive scanners.

Real-world (and common test) targets vary: some only serve HTTPS, some
only serve plain HTTP, some both. Rather than hardcoding one scheme,
every scanner tries HTTPS first (the common case for production sites)
and falls back to HTTP so a single domain string works either way.
"""

import requests

DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {"User-Agent": "SentraScan/1.0"}


def base_url_candidates(domain: str) -> list[str]:
    return [f"https://{domain}", f"http://{domain}"]


def get(domain: str, path: str = "", **kwargs) -> tuple[requests.Response, str]:
    """GETs domain+path, trying HTTPS then HTTP. Returns (response, base_url_used)."""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("headers", DEFAULT_HEADERS)

    last_exc: requests.RequestException | None = None
    for base_url in base_url_candidates(domain):
        try:
            resp = requests.get(f"{base_url}{path}", **kwargs)
            return resp, base_url
        except requests.RequestException as exc:
            last_exc = exc
            continue

    assert last_exc is not None
    raise last_exc
