from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

STRIP_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                "utm_content", "trk", "refId", "trackingId", "ref", "fbclid"}

def normalize_url(url: str) -> str:
    """Strip tracking params and normalize URL for dedup comparison."""
    if not url:
        return ""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    filtered = {k: v for k, v in params.items() if k not in STRIP_PARAMS}
    clean_query = urlencode(filtered, doseq=True)
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path.rstrip("/"),
        parsed.params, clean_query, ""
    )).lower()
