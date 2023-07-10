import logging
import time

logger = logging.getLogger(__name__)


def get_steam_json(s, url, appid):
    sleep_time = 10
    while True:
        result = s.get(url)
        if result.status_code == 429:
            logger.warning("Rate-limit detected, waiting for %s seconds.", sleep_time)
            time.sleep(sleep_time)
            sleep_time += 5
        else:
            break
    if result.text != "":
        return result.json()
    return {str(appid): {"success": False}}


def get_json(s, url):
    return s.get(url).json()
