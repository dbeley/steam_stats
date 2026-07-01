import sys
import logging
import time
import argparse
import csv
import requests
import pandas as pd
from pathlib import Path
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Allow running from the scripts/ directory directly
_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir.parent))

from steam_stats.config import SteamConfig  # noqa: E402
from steam_stats.requests import DEFAULT_TIMEOUT  # noqa: E402

logger = logging.getLogger()
START_TIME = time.time()


def create_session():
    """Create a requests session with retry configuration."""
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def get_all_ids(api_key):
    url = f"http://api.steampowered.com/ISteamApps/GetAppList/v0002/?key={api_key}&format=json"
    logger.info("Fetching full Steam app list (this may take a moment)...")
    s = create_session()
    try:
        response = s.get(url, timeout=60)
        response.raise_for_status()
        json_dict = response.json()
    except Exception as e:
        logger.error("Failed to fetch app list: %s", e)
        return []
    app_list = json_dict.get("applist", {}).get("apps", [])
    logger.debug("Fetched %d total apps", len(app_list))
    return [{"appid": game["appid"]} for game in app_list]


def get_owned_ids(api_key, user_id):
    url = (
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={api_key}&steamid={user_id}&format=json&include_played_free_games=1"
    )
    s = create_session()
    try:
        response = s.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        json_dict = response.json()
    except Exception as e:
        logger.error("Failed to fetch owned games: %s", e)
        return []
    games = json_dict.get("response", {}).get("games", [])
    logger.debug("Found %d owned games", len(games))
    return [{"appid": game["appid"]} for game in games]


def get_wishlist_ids(user_id):
    dict_games = []
    url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?steamid={user_id}"
    s = create_session()
    try:
        logger.info("Fetching wishlist: %s", url)
        response = s.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        json_dict = response.json()
    except Exception as e:
        logger.error("Failed to fetch wishlist: %s", e)
        return []
    if json_dict:
        items = json_dict.get("response", {}).get("items", [])
        logger.debug("Found %d items in wishlist", len(items))
        for game_data in items:
            dict_games.append({"appid": game_data["appid"]})
    return dict_games


def main():
    args = parse_args()
    if not args.type:
        raise ValueError("-t/--type argument required. Exiting.")
    if args.type not in ["all", "owned", "wishlist", "both"]:
        raise ValueError(f"Type {args.type} not supported. Exiting.")

    config = SteamConfig()
    api_key = config.get_api_key()
    user_id = config.get_user_id(override=args.user_id)

    Path("Exports").mkdir(parents=True, exist_ok=True)

    if args.type == "all":
        logger.debug("Type: all")
        dict_games = get_all_ids(api_key)
    elif args.type == "owned":
        logger.debug("Type: owned")
        dict_games = get_owned_ids(api_key, user_id)
    elif args.type == "wishlist":
        logger.debug("Type: wishlist")
        dict_games = get_wishlist_ids(user_id)
    elif args.type == "both":
        logger.debug("Type: both")
        dict_games = get_owned_ids(api_key, user_id)
        dict_games += get_wishlist_ids(user_id)

    df = pd.DataFrame(dict_games)
    filename = (
        args.filename if args.filename else f"Exports/ids_{args.type}_{user_id}.csv"
    )
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info("Output file: %s.", filename)

    logger.info("Runtime : %.2f seconds.", time.time() - START_TIME)


def parse_args():
    parser = argparse.ArgumentParser(description="export ids of a set of games")
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "-t",
        "--type",
        help="Type of ids to export (all, owned, wishlist or both (owned and wishlist))",
        type=str,
    )
    parser.add_argument(
        "-u",
        "--user_id",
        help="User id to extract the games data from (steamID64). Default: user in config.ini",
        type=str,
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Override export filename.",
        type=str,
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
