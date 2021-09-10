import requests
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)


def get_steam_json(url, appid):
    s = requests.Session()
    logger.debug(f"get_json {url}")
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    result = s.get(url)
    if result.text != "":
        return result.json()
    return {str(appid): {"success": False}}


def get_json(url):
    s = requests.Session()
    logger.debug(f"get_json {url}")
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s.get(url).json()
