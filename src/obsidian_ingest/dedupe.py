from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "spm",
}


def normalize_source_key(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
        return _normalize_url(parsed)
    if not parsed.scheme or len(parsed.scheme) == 1:
        return str(Path(raw).expanduser())
    return raw


def _normalize_url(parsed) -> str:
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else parsed.netloc.lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_key(key)
    ]
    query = urlencode(sorted(query_items), doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def _is_tracking_key(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS
