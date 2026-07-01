import logging
from .requests import get_json

logger = logging.getLogger(__name__)

ITAD_REGION = "eu1"
ITAD_COUNTRY = "FR"


def get_itad_plain(s, api_key, appid):
    url = (
        "https://api.isthereanydeal.com/"
        f"v02/game/plain/?key={api_key}"
        f"&shop=steam&game_id=app%2F{appid}&url=&title=&optional="
    )
    result = get_json(s, url)
    if not result:
        logger.debug("No result for ITAD plain lookup (appid %s)", appid)
        return None

    logger.debug("ITAD plain result for %s: %s", appid, result)
    data = result.get("data")
    if isinstance(data, dict) and "plain" in data:
        return data["plain"]

    logger.debug("No ITAD plain found for appid %s", appid)
    return None


def get_itad_historical_low(
    s, api_key, plain, region=ITAD_REGION, country=ITAD_COUNTRY
):
    url = (
        "https://api.isthereanydeal.com/v01/game/lowest/"
        f"?key={api_key}&plains={plain}&region={region}&country={country}"
    )
    result = get_json(s, url)
    if not result:
        return None

    game_data = result.get("data", {}).get(plain)
    if not game_data:
        return None

    return {
        "historical_low_price": game_data.get("price"),
        "historical_low_currency": result.get(".meta", {}).get("currency"),
        "historical_low_shop": game_data.get("shop", {}).get("name"),
    }


def get_itad_current_price(
    s, api_key, appid, plain, region=ITAD_REGION, country=ITAD_COUNTRY
):
    url = (
        "https://api.isthereanydeal.com/v01/game/prices/"
        f"?key={api_key}&plains={plain}&region={region}&country={country}"
        "&shops=steam&added=0"
    )
    result = get_json(s, url)
    if not result:
        return None

    plain_data = result.get("data", {}).get(plain, {})
    prices_list = plain_data.get("list", [])
    if not prices_list:
        return None

    # Sometimes there are several entries for one game. Get the one with the
    # correct Steam URL.
    correct_result = None
    for x in prices_list:
        if str(appid) in x.get("url", ""):
            correct_result = x
            break

    if not correct_result:
        logger.debug(
            "No Steam price entry found for appid %s (plain %s), using first entry",
            appid,
            plain,
        )
        correct_result = prices_list[0]

    logger.debug("ITAD price for %s: %s", appid, correct_result)
    return {
        "current_price_price": correct_result.get("price_new"),
        "current_price_currency": result.get(".meta", {}).get("currency"),
        "current_price_shop": correct_result.get("shop", {}).get("name"),
    }


def get_itad_data(s, api_key, appid):
    """Fetch ITAD price data for a single game.

    Returns a dict with price fields or None on failure.
    """
    plain = get_itad_plain(s, api_key, appid)
    if not plain:
        logger.debug("No ITAD plain for appid %s, skipping price data", appid)
        return None

    historical_low = get_itad_historical_low(s, api_key, plain)
    current_price = get_itad_current_price(s, api_key, appid, plain)

    if not historical_low and not current_price:
        logger.debug("No ITAD price data for appid %s", appid)
        return None

    result = {"appid": appid, "plain": plain}
    if historical_low:
        result.update(historical_low)
    if current_price:
        result.update(current_price)
    return result
