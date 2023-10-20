"""
steam_stats : extract steam game data from a list of steam appids.
"""
import logging
import time
import argparse
import configparser
import datetime
import pandas as pd
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
from tqdm import tqdm
from .itad import get_itad_data
from .requests import get_steam_json

logger = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
START_TIME = time.time()
DELAY = 60


def get_achievements_dict(s, api_key, user_id, app_id):
    url_achievements = (
        "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
        f"?appid={app_id}&key={api_key}&steamid={user_id}"
    )
    result = get_steam_json(s, url_achievements, app_id)
    if "error" in result["playerstats"].keys():
        if result["playerstats"]["error"] == "Requested app has no stats":
            return {}
        breakpoint()
    return {
        "appid": app_id,
        "achieved": sum(
            [
                achievement["achieved"] == 1
                for achievement in result["playerstats"]["achievements"]
            ]
        )
        if "achievements" in result["playerstats"].keys()
        else None,
        "total_achievements": len(result["playerstats"]["achievements"])
        if "achievements" in result["playerstats"].keys()
        else None,
    }


def get_data_dict(s, game_id: str) -> dict[str, str]:
    url_game = f"http://store.steampowered.com/api/appdetails?appids={game_id}"
    result = get_steam_json(s, url_game, game_id)
    game_result = result[str(game_id)]
    if success := game_result.get("success"):
        logger.debug("ID %s - success : %s", game_id, success)
        data_dict = game_result["data"]
        return data_dict
    else:
        logger.warning(
            "Couldn't extract data for game %s: %s",
            game_id,
            game_result,
        )
        return {}


def get_reviews_dict(s, game_id):
    url_reviews = (
        f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
    )
    result = get_steam_json(s, url_reviews, game_id)
    reviews_dict = result["query_summary"]
    return reviews_dict


def main():
    args = parse_args()
    export_date = datetime.datetime.now().strftime("%Y-%m-%d")
    export_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not args.file:
        raise ValueError("-f/--file argument not filled. Exiting.")
    if not Path(args.file).is_file():
        raise FileNotFoundError("%s is not a file. Exiting.", args.file)

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    config.read("config.ini")

    logger.debug("Reading CSV file")
    df = pd.read_csv(args.file, sep="\t|;", engine="python")
    logger.debug("Columns : %s", df.columns)

    ids = df.appid.tolist()
    Path("Exports").mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))

    game_dict_list = []
    for game_id in tqdm(ids, dynamic_ncols=True):
        if data_dict := get_data_dict(s, game_id):
            reviews_dict = get_reviews_dict(s, game_id)
            achievements_dict = get_achievements_dict(
                s, config["steam"]["api_key"], config["steam"]["user_id"], game_id
            )
            game_dict = {
                "export_date": export_time,
                "name": data_dict["name"].strip(),
                "appid": game_id,
                "type": data_dict.get("type"),
                "required_age": data_dict.get("required_age"),
                "is_free": data_dict.get("is_free"),
                "developers": ", ".join(data_dict.get("developers", [])),
                "publishers": ", ".join(data_dict.get("publishers", [])),
                "windows": data_dict["platforms"]["windows"],
                "linux": data_dict["platforms"]["linux"],
                "mac": data_dict["platforms"]["mac"],
                "genres": ", ".join(
                    [x["description"] for x in data_dict.get("genres", [])]
                ),
                "release_date": data_dict["release_date"]["date"],
                "num_reviews": reviews_dict.get("num_reviews"),
                "review_score": reviews_dict.get("review_score"),
                "review_score_desc": reviews_dict.get("review_score_desc"),
                "total_positive": reviews_dict.get("total_positive"),
                "total_negative": reviews_dict.get("total_negative"),
                "total_reviews": reviews_dict.get("total_reviews"),
                "url": f"https://store.steampowered.com/app/{game_id}",
                "achieved_achievements": achievements_dict.get("achieved"),
                "total_achievements": achievements_dict.get("total_achievements"),
            }

            if args.export_extra_data:
                result_itad = get_itad_data(s, config["itad"]["api_key"], game_id)
                if result_itad:
                    game_dict = {**game_dict, **result_itad}

            logger.debug("Result for game %s: %s.", game_id, game_dict)
            game_dict_list.append(game_dict)

    df = pd.DataFrame(game_dict_list)
    df = df.astype(
        {
            "achieved_achievements": "Int64",
            "total_achievements": "Int64",
            "total_positive": "Int64",
            "total_negative": "Int64",
            "total_reviews": "Int64",
        }
    )

    filename = (
        args.export_filename
        if args.export_filename
        else f"Exports/game_info_{export_date}.csv"
    )
    logger.debug("Writing complete export %s.", filename)
    df.to_csv(filename, sep="\t", index=False)
    logger.info("Runtime : %.2f seconds" % (time.time() - START_TIME))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Steam games data from a list of appids"
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
        "-f", "--file", help="File containing the appids to parse", type=str
    )
    parser.add_argument("--export_filename", help="Override export filename", type=str)
    parser.add_argument(
        "--export_extra_data",
        help="Enable extra data fetching (ITAD)",
        dest="export_extra_data",
        action="store_true",
    )
    parser.set_defaults(export_extra_data=False)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
