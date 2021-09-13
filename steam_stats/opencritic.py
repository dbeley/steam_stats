from .requests import get_json
import logging

logger = logging.getLogger(__name__)


def get_opencritic_id(s, search):
    url = f"https://api.opencritic.com/api/game/search?criteria={search}"
    result = get_json(s, url)

    if result:
        return result[0]["id"]
    else:
        return None


def get_opencritic_infos(s, search):
    opencritic_id = get_opencritic_id(s, search)
    if opencritic_id:
        url = f"https://api.opencritic.com/api/game/{opencritic_id}"
        result = get_json(s, url)

        return {
            "opencritic_tier": result["tier"],
            "opencritic_median_score": result["medianScore"]
            if result["medianScore"] != -1.0
            else None,
            "opencritic_reviews_number": result["numReviews"],
        }
    return None
