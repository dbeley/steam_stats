"""
steam_stats : extract steam game informations from a list of steam appids.
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
from .itad import get_itad_infos
from .hltb import get_howlongtobeat_infos
from .opencritic import get_opencritic_infos
from .requests import get_steam_json
from .utils import slugify

logger = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
START_TIME = time.time()
DELAY = 60


def get_info_dict(s, game_id):
    success = False
    n_tries = 0
    while True:
        n_tries += 1
        url_info_game = f"http://store.steampowered.com/api/appdetails?appids={game_id}"
        result = get_steam_json(s, url_info_game, game_id)
        if result:
            success = result[str(game_id)]["success"]
            if success:
                logger.debug("ID %s - success : %s", game_id, success)
                info_dict = result[str(game_id)]["data"]
                return info_dict
            else:
                return None
        else:
            logger.warning(
                f"get_info_dict: No result for {url_info_game}. Retrying in {DELAY} seconds: try {n_tries}."
            )
            time.sleep(DELAY)


def get_reviews_dict(s, game_id):
    n_tries = 0
    while True:
        n_tries += 1
        url_reviews = (
            f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
        )
        result = get_steam_json(s, url_reviews, game_id)
        if result:
            reviews_dict = result["query_summary"]
            return reviews_dict
        else:
            logger.warning(
                f"get_reviews_dict: No result for {url_reviews}. Retrying in {DELAY} seconds: try {n_tries}."
            )
            time.sleep(DELAY)


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
        info_dict = get_info_dict(s, game_id)
        reviews_dict = get_reviews_dict(s, game_id)
        game_dict = {
            "export_date": export_time,
            "name": info_dict.get("name").strip(),
            "appid": game_id,
            "type": info_dict.get("type"),
            "required_age": info_dict.get("required_age"),
            "is_free": info_dict.get("is_free"),
            "developers": ", ".join(info_dict.get("developers")),
            "publishers": ", ".join(info_dict.get("publishers")),
            "windows": info_dict.get("platforms").get("windows"),
            "linux": info_dict.get("platforms").get("linux"),
            "mac": info_dict.get("platforms").get("mac"),
            "genres": ", ".join([x["description"] for x in info_dict.get("genres")]),
            "release_date": info_dict.get("release_date").get("date"),
            "num_reviews": reviews_dict.get("num_reviews"),
            "review_score": reviews_dict.get("review_score"),
            "review_score_desc": reviews_dict.get("review_score_desc"),
            "total_positive": reviews_dict.get("total_positive"),
            "total_negative": reviews_dict.get("total_negative"),
            "total_reviews": reviews_dict.get("total_reviews"),
            "url": f"https://store.steampowered.com/app/{game_id}",
        }

        if args.extra_infos:
            name = info_dict.get("name").strip()
            result_itad = get_itad_infos(s, config["itad"]["api_key"], game_id)
            if result_itad:
                game_dict = {**game_dict, **result_itad}
            # result_opencritic = get_opencritic_infos(s, name)
            # if result_opencritic:
            #     game_dict = {**game_dict, **result_opencritic}
            result_howlongtobeat = get_howlongtobeat_infos(name)
            if result_howlongtobeat:
                game_dict = {**game_dict, **result_howlongtobeat}

        logger.debug("Result for game %s: %s.", game_id, game_dict)
        game_dict_list.append(game_dict)

        if args.separate_export:
            df = pd.DataFrame([game_dict], index=[0])
            if game_dict.get("name"):
                filename = (
                    f"Exports/{game_id}_{slugify(game_dict['name'])}_{export_date}.csv"
                )
            else:
                filename = f"Exports/{game_id}.csv"
            logger.debug("Writing partial export %s.", filename)
            df.to_csv(filename, sep="\t", index=False)

    df = pd.DataFrame(game_dict_list)

    filename = (
        args.export_filename
        if args.export_filename
        else f"Exports/game_info_{export_date}.csv"
    )
    logger.debug("Writing complete export %s.", filename)
    df.to_csv(filename, sep="\t", index=False)
    logger.info("Runtime : %.2f seconds" % (time.time() - START_TIME))


def parse_args():
    parser = argparse.ArgumentParser(description="Export games info from a list of ids")
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "-f", "--file", help="File containing the ids to parse", type=str
    )
    parser.add_argument("--export_filename", help="Override export filename.", type=str)
    parser.add_argument(
        "-s",
        "--separate_export",
        help="Export separately (one file per game + the global file)",
        dest="separate_export",
        action="store_true",
    )
    parser.add_argument(
        "--extra_infos",
        help="Enable extra information fetching (ITAD, HLTB, opencritic).",
        dest="extra_infos",
        action="store_true",
    )
    parser.set_defaults(separate_export=False, extra_infos=False)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
