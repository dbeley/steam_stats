import logging
from .requests import get_json

logger = logging.getLogger(__name__)


def get_itad_plain(s, api_key, appid):
    url = (
        "https://api.isthereanydeal.com/"
        f"v02/game/plain/?key={api_key}"
        f"&shop=steam&game_id=app%2F{appid}&url=&title=&optional="
    )
    result = get_json(s, url)
    logger.debug(f"{url}: {result}")
    if result:
        if isinstance(result["data"], dict):
            if "plain" in result["data"]:
                return result["data"]["plain"]
    return None


def get_itad_historical_low(s, api_key, plain, region, country):
    url = (
        "https://api.isthereanydeal.com/v01/game/lowest/"
        f"?key={api_key}&plains={plain}&region={region}&country={country}"
    )
    result = get_json(s, url)
    logger.debug(f"{url}: {result}")
    if result and plain in result["data"]:
        return {
            "historical_low_price": result["data"][plain]["price"]
            if "price" in result["data"][plain]
            else None,
            "historical_low_currency": result[".meta"]["currency"]
            if "currency" in result["data"][plain]
            else None,
            "historical_low_shop": result["data"][plain]["shop"]["name"]
            if "shop" in result["data"][plain]
            else None,
        }
    else:
        return None


def get_itad_current_price(s, api_key, appid, plain, region, country):
    url = (
        "https://api.isthereanydeal.com/v01/game/prices/"
        f"?key={api_key}&plains={plain}&region={region}&country={country}"
        "&shops=steam&added=0"
    )
    result = get_json(s, url)
    # for some reasons there are sometimes several entries for one game. Get the one with the correct Steam URL.
    correct_result = None
    for x in result["data"][plain]["list"]:
        if str(appid) in x["url"]:
            correct_result = x
    logger.debug(f"{url}: {correct_result}")
    if correct_result:
        return {
            "current_price_price": correct_result["price_new"]
            if "price_new" in correct_result
            else None,
            "current_price_currency": result[".meta"]["currency"]
            if ".meta" in correct_result
            else None,
            "current_price_shop": correct_result["shop"]["name"]
            if "shop" in correct_result
            else None,
        }
    else:
        return None


def get_itad_data(s, api_key, appid):
    # plain is the internal itad id for a game
    plain = get_itad_plain(s, api_key, appid)
    if plain:
        historical_low = get_itad_historical_low(s, api_key, plain, "eu1", "FR")
        current_price = get_itad_current_price(s, api_key, appid, plain, "eu1", "FR")
    else:
        historical_low = None
        current_price = None
    if plain and historical_low and current_price:
        return {
            "appid": appid,
            "plain": plain,
            "historical_low_price": historical_low["historical_low_price"]
            if "historical_low_price" in historical_low
            else None,
            "historical_low_currency": historical_low["historical_low_currency"]
            if "historical_low_currency" in historical_low
            else None,
            "historical_low_shop": historical_low["historical_low_shop"]
            if "historical_low_shop" in historical_low
            else None,
            "current_price_price": current_price["current_price_price"]
            if "current_price_price" in current_price
            else None,
            "current_price_currency": current_price["current_price_currency"]
            if "current_price_currency" in current_price
            else None,
            "current_price_shop": current_price["current_price_shop"]
            if "current_price_shop" in current_price
            else None,
        }
    else:
        return None
