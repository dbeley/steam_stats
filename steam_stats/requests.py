import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)


def get_steam_json(s, url, appid):
    logger.debug(f"get_json {url}")
    result = s.get(url)
    if result.text != "":
        return result.json()
    return {str(appid): {"success": False}}


def get_json(s, url):
    logger.debug(f"get_json {url}")
    return s.get(url).json()
