import logging
import urllib.parse

import requests
import urllib3.exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

# Query parameters whose values must never be written to logs.
SENSITIVE_QUERY_PARAMS = frozenset({"key", "steamid", "api_key"})


def redact_url(url: str) -> str:
    """Return ``url`` with secret query parameter values replaced.

    Steam API keys and Steam IDs are passed as query parameters. Logging the
    full URL would leak them into logs/journald, so they are masked first.
    """
    parsed = urllib.parse.urlsplit(url)
    if not parsed.query:
        return url
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [
        (name, "REDACTED" if name.lower() in SENSITIVE_QUERY_PARAMS else value)
        for name, value in query
    ]
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(redacted))
    )


def create_session(workers: int = 10) -> requests.Session:
    """Create a requests Session with retry configuration and connection pooling.

    urllib3 handles retries for 429/5xx and transient network errors (honouring
    ``Retry-After``), so ``get_steam_json``/``get_json`` only inspect the final
    response rather than retrying again themselves.
    """
    pool_size = max(20, workers)
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=pool_size,
        pool_maxsize=pool_size,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def safe_json_response(response: requests.Response) -> dict | None:
    """Safely parse a JSON response, returning None on failure."""
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, ValueError) as e:
        logger.warning(
            "Non-JSON response from %s (status %s): %s",
            redact_url(response.url),
            response.status_code,
            e,
        )
        return None


def _error(appid, message: str) -> dict:
    return {str(appid): {"success": False, "error": message}}


def get_steam_json(s, url, appid, timeout=DEFAULT_TIMEOUT):
    """Fetch JSON from a Steam API endpoint.

    Retries for 429/5xx and network errors are performed by the session's
    urllib3 retry configuration (see :func:`create_session`); after those are
    exhausted urllib3 raises a ``RequestException`` which is turned into an
    error payload here. Steam frequently returns useful error information in
    the body of 4xx responses (e.g. achievements "no stats"), so those bodies
    are still parsed when present.
    """
    try:
        result = s.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        logger.warning("Network error fetching %s: %s", redact_url(url), e)
        return _error(appid, str(e))

    if result.status_code == 429 or result.status_code >= 500:
        logger.warning("HTTP %s for %s", result.status_code, redact_url(url))
        return _error(appid, f"HTTP {result.status_code}")

    if result.status_code >= 400:
        logger.debug(
            "Status %s for %s — body may contain error info.",
            result.status_code,
            redact_url(url),
        )
        if result.text:
            json_data = safe_json_response(result)
            if json_data is not None:
                return json_data
        return _error(appid, f"HTTP {result.status_code}")

    if not result.text:
        return _error(appid, "Empty response")

    json_data = safe_json_response(result)
    if json_data is None:
        return _error(appid, "Invalid JSON")
    return json_data


def get_json(s, url, timeout=DEFAULT_TIMEOUT):
    """Fetch JSON from a generic API endpoint.

    Returns None on any failure instead of raising.
    """
    try:
        result = s.get(url, timeout=timeout)
        result.raise_for_status()
    except (
        requests.exceptions.RequestException,
        urllib3.exceptions.HTTPError,
    ) as e:
        logger.warning("Request failed for %s: %s", redact_url(url), e)
        return None
    return safe_json_response(result)
