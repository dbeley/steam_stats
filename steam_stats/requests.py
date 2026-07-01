import logging
import time

import requests
import urllib3.exceptions

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
MAX_RATE_LIMIT_SLEEP = 120


def safe_json_response(response: requests.Response) -> dict | None:
    """Safely parse a JSON response, returning None on failure."""
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, ValueError) as e:
        logger.warning(
            "Non-JSON response from %s (status %s): %s",
            response.url,
            response.status_code,
            e,
        )
        return None


def get_steam_json(s, url, appid, timeout=DEFAULT_TIMEOUT):
    """Fetch JSON from a Steam API endpoint with rate-limit handling.

    - 429 (rate-limited): retries with exponential backoff (up to 10 attempts)
    - 5xx (server errors): retries up to 10 attempts, then returns error dict
    - 4xx (client errors, excl 429): tries to parse JSON body — many Steam
      endpoints return useful error payloads (e.g. achievements "no stats")
    - 200: returns parsed JSON normally
    """
    sleep_time = 10
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            result = s.get(url, timeout=timeout)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            urllib3.exceptions.ProtocolError,
        ) as e:
            logger.warning(
                "Network error fetching %s (attempt %d/%d): %s",
                url,
                attempt + 1,
                max_attempts,
                e,
            )
            if attempt < max_attempts - 1:
                time.sleep(sleep_time)
                sleep_time = min(sleep_time + 5, MAX_RATE_LIMIT_SLEEP)
                continue
            return {str(appid): {"success": False, "error": str(e)}}

        if result.status_code == 429:
            logger.warning(
                "Rate-limit detected, waiting %s seconds (attempt %d/%d).",
                sleep_time,
                attempt + 1,
                max_attempts,
            )
            time.sleep(sleep_time)
            sleep_time = min(sleep_time + 5, MAX_RATE_LIMIT_SLEEP)
            continue

        if result.status_code >= 500:
            logger.warning(
                "Server error %s for %s (attempt %d/%d).",
                result.status_code,
                url,
                attempt + 1,
                max_attempts,
            )
            if attempt < max_attempts - 1:
                time.sleep(sleep_time)
                sleep_time = min(sleep_time + 5, MAX_RATE_LIMIT_SLEEP)
                continue
            return {
                str(appid): {"success": False, "error": f"HTTP {result.status_code}"}
            }

        # 4xx (except 429 handled above): try to parse the JSON body — many
        # Steam endpoints return useful error info (e.g. achievements "no stats")
        # in the response body even on 4xx.
        if 400 <= result.status_code < 500:
            logger.debug(
                "Status %s for %s — body may contain error info.",
                result.status_code,
                url,
            )
            if result.text:
                json_data = safe_json_response(result)
                if json_data is not None:
                    return json_data
            return {
                str(appid): {
                    "success": False,
                    "error": f"HTTP {result.status_code}",
                }
            }

        break
    else:
        logger.error("Exhausted retries for %s", url)
        return {str(appid): {"success": False, "error": "Max retries exceeded"}}

    if not result.text:
        return {str(appid): {"success": False, "error": "Empty response"}}

    json_data = safe_json_response(result)
    if json_data is None:
        return {str(appid): {"success": False, "error": "Invalid JSON"}}
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
        logger.warning("Request failed for %s: %s", url, e)
        return None
    return safe_json_response(result)
