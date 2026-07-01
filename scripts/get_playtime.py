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


def get_playtime_recent(api_key, user_id):
    url_recent = (
        "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"
        f"?key={api_key}&steamid={user_id}"
    )
    s = create_session()
    try:
        response = s.get(url_recent, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        json_dict = response.json()
    except Exception as e:
        logger.error("Failed to fetch recently played games: %s", e)
        return []

    games = json_dict.get("response", {}).get("games", [])
    return [
        {
            "appid": game["appid"],
            "playtime_2weeks": int(game.get("playtime_2weeks", 0)),
        }
        for game in games
    ]


def get_playtime(api_key, user_id):
    url = (
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={api_key}&steamid={user_id}&format=json&include_played_free_games=1"
    )
    s = create_session()
    try:
        response = s.get(url, timeout=60)
        response.raise_for_status()
        json_dict = response.json()
    except Exception as e:
        logger.error("Failed to fetch playtime data: %s", e)
        return []

    games = json_dict.get("response", {}).get("games", [])
    return [
        {
            "appid": game["appid"],
            "playtime": game.get("playtime_forever", 0),
            "playtime_windows": game.get("playtime_windows_forever", 0),
            "playtime_mac": game.get("playtime_mac_forever", 0),
            "playtime_linux": game.get("playtime_linux_forever", 0),
        }
        for game in games
    ]


def main():
    args = parse_args()

    config = SteamConfig()
    api_key = config.get_api_key()
    user_id = config.get_user_id(override=args.user_id)

    Path("Exports").mkdir(parents=True, exist_ok=True)

    dict_games = get_playtime(api_key, user_id)
    if not dict_games:
        logger.warning("No playtime data returned. Check your API key and user ID.")
        return

    dict_games_recent = get_playtime_recent(api_key, user_id)

    df = pd.DataFrame(dict_games)
    df_recent = pd.DataFrame(dict_games_recent)
    df = pd.merge(df, df_recent, how="left", on=["appid"])
    df["playtime_2weeks"] = df["playtime_2weeks"].fillna(0.0).astype(int)
    filename = args.filename if args.filename else f"Exports/playtime_{user_id}.csv"
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info("Output file: %s.", filename)

    logger.info("Runtime : %.2f seconds.", time.time() - START_TIME)


def parse_args():
    parser = argparse.ArgumentParser(
        description="export playtime of games played by a Steam user."
    )
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
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
