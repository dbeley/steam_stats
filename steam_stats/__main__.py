"""
steam_stats : extract steam game informations from a list of steam appids.
"""
import logging
import time
import argparse
import configparser
import requests
import datetime
import pandas as pd
import unicodedata
import re
from pathlib import Path
from tqdm import tqdm
from .itad import get_itad_infos
from .hltb import get_howlongtobeat_infos
from .opencritic import get_opencritic_infos
from .requests import get_json

logger = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
START_TIME = time.time()


def get_entry_from_dict(title, entry):
    if title:
        if entry in title:
            return title[entry]
        else:
            return ""
    else:
        return ""


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def get_info_dict(game_id):
    success = False
    n_tries = 0
    while True:
        n_tries += 1
        url_info_game = f"http://store.steampowered.com/api/appdetails?appids={game_id}"
        result = get_json(url_info_game)
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
                f"get_info_dict: No result for {url_info_game}. Retrying in 10 seconds: try {n_tries}."
            )
            time.sleep(10)


def get_reviews_dict(game_id):
    n_tries = 0
    while True:
        n_tries += 1
        url_reviews = (
            f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
        )
        result = get_json(url_reviews)
        if result:
            reviews_dict = result["query_summary"]
            return reviews_dict
        else:
            logger.warning(
                f"get_reviews_dict: No result for {url_reviews}. Retrying in 10 seconds: try {n_tries}."
            )
            time.sleep(10)


def main():
    args = parse_args()
    auj = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not args.file:
        logger.error("-f/--file argument not filled. Exiting.")
        exit()

    if not Path(args.file).is_file():
        logger.error("%s is not a file. Exiting.", args.file)
        exit()

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    config.read("config.ini")
    try:
        api_key = config["steam"]["api_key"]
    except Exception as e:
        logger.error(f"Problem with the config file: {e}.")
        exit()

    logger.debug("Reading CSV file")
    df = pd.read_csv(args.file, sep="\t|;", engine="python")
    logger.debug("Columns : %s", df.columns)

    ids = df.appid.tolist()

    Path("Exports").mkdir(parents=True, exist_ok=True)

    game_dict_list = []
    for game_id in tqdm(ids, dynamic_ncols=True):
        info_dict = get_info_dict(game_id)
        reviews_dict = get_reviews_dict(game_id)
        game_dict = {
            "export_date": auj,
            "name": get_entry_from_dict(info_dict, "name").strip(),
            "appid": game_id,
            "type": get_entry_from_dict(info_dict, "type"),
            "required_age": get_entry_from_dict(info_dict, "required_age"),
            "is_free": get_entry_from_dict(info_dict, "is_free"),
            "developers": ", ".join(get_entry_from_dict(info_dict, "developers")),
            "publishers": ", ".join(get_entry_from_dict(info_dict, "publishers")),
            "windows": get_entry_from_dict(
                get_entry_from_dict(info_dict, "platforms"), "windows"
            ),
            "linux": get_entry_from_dict(
                get_entry_from_dict(info_dict, "platforms"), "linux"
            ),
            "mac": get_entry_from_dict(
                get_entry_from_dict(info_dict, "platforms"), "mac"
            ),
            "genres": ", ".join(
                [x["description"] for x in get_entry_from_dict(info_dict, "genres")]
            ),
            "release_date": get_entry_from_dict(
                get_entry_from_dict(info_dict, "release_date"), "date"
            ),
            "num_reviews": get_entry_from_dict(reviews_dict, "num_reviews"),
            "review_score": get_entry_from_dict(reviews_dict, "review_score"),
            "review_score_desc": get_entry_from_dict(reviews_dict, "review_score_desc"),
            "total_positive": get_entry_from_dict(reviews_dict, "total_positive"),
            "total_negative": get_entry_from_dict(reviews_dict, "total_negative"),
            "total_reviews": get_entry_from_dict(reviews_dict, "total_reviews"),
            "url": f"https://store.steampowered.com/app/{game_id}",
        }

        if args.extra_infos:
            api_key = config["itad"]["api_key"]
            name = get_entry_from_dict(info_dict, "name").strip()
            result_itad = get_itad_infos(api_key, game_id)
            if result_itad:
                game_dict = {**game_dict, **result_itad}
            result_opencritic = get_opencritic_infos(name)
            if result_opencritic:
                game_dict = {**game_dict, **result_opencritic}
            result_howlongtobeat = get_howlongtobeat_infos(name)
            if result_howlongtobeat:
                game_dict = {**game_dict, **result_howlongtobeat}

        logger.debug("Result for game %s: %s.", game_id, game_dict)
        game_dict_list.append(game_dict)

        if args.separate_export:
            # have to put the dict in a list for some reason
            df = pd.DataFrame([game_dict], index=[0])
            if game_dict.get("name"):
                filename = f"Exports/{game_id}_{slugify(game_dict['name'])}_{auj}.csv"
            else:
                filename = f"Exports/{game_id}.csv"
            logger.debug("Writing partial export %s.", filename)
            df.to_csv(filename, sep="\t", index=False)

    df = pd.DataFrame(game_dict_list)

    filename = (
        args.export_filename if args.export_filename else f"Exports/game_info_{auj}.csv"
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
