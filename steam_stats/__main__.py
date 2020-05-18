"""
Steam script
"""
import logging
import time
import argparse
import configparser
import requests
import datetime
import pandas as pd
import unicodedata
import random
import re
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
temps_debut = time.time()


def get_entry_from_dict(title, entry):
    if entry in title:
        return title[entry]
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
    info_dict = {}
    success = "false"
    n_tries = 0
    while True:
        n_tries += 1
        try:
            url_info_game = (
                f"http://store.steampowered.com/api/appdetails?appids={game_id}"
            )
            info_dict = requests.get(url_info_game).json()
            success = info_dict[str(game_id)]["success"]
            logger.debug("ID %s - success : %s", game_id, success)
            info_dict = info_dict[str(game_id)]["data"]
        except Exception as e:
            logger.debug(
                "Can't extract page for ID %s - %s : %s", game_id, url_info_game, e,
            )
            time.sleep(2)
        if success == "true" or n_tries > 3:
            break
    return info_dict


def get_reviews_dict(game_id):
    reviews_dict = {}
    n_tries = 0
    while True:
        n_tries += 1
        try:
            url_reviews = f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
            reviews_dict = requests.get(url_reviews).json()
            reviews_dict = reviews_dict["query_summary"]
        except Exception as e:
            logger.debug(
                "Can't extract reviews for ID %s - %s : %s", game_id, url_reviews, e
            )
            time.sleep(2)
        if get_entry_from_dict(reviews_dict, "num_reviews") or n_tries > 3:
            break
    return reviews_dict


def main():
    args = parse_args()
    file = args.file
    separate_export = args.separate_export

    if not file:
        logger.error("-f/--file argument not filled. Exiting.")
        exit()

    if not Path(file).is_file():
        logger.error("%s is not a file. Exiting.", file)
        exit()

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    config.read("config.ini")
    try:
        api_key = config["steam"]["api_key"]
    except Exception as e:
        logger.error("Problem with the config file.")
        exit()

    logger.debug("Reading CSV file")
    df = pd.read_csv(file, sep="\t|;", engine="python")
    logger.debug("Columns : %s", df.columns)

    ids = df.appid.tolist()

    Path("Exports").mkdir(parents=True, exist_ok=True)

    game_dict_list = []
    for game_id in tqdm(ids):
        time.sleep(2)
        info_dict = get_info_dict(game_id)
        if info_dict:
            reviews_dict = get_reviews_dict(game_id)
            if reviews_dict:
                auj = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                game_dict = {
                    "export_date": auj,
                    "appid": game_id,
                    "name": get_entry_from_dict(info_dict, "name").strip(),
                    "type": get_entry_from_dict(info_dict, "type"),
                    "required_age": get_entry_from_dict(info_dict, "required_age"),
                    "is_free": get_entry_from_dict(info_dict, "is_free"),
                    "developers": ", ".join(
                        get_entry_from_dict(info_dict, "developers")
                    ),
                    "publishers": ", ".join(
                        get_entry_from_dict(info_dict, "publishers")
                    ),
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
                        [
                            x["description"]
                            for x in get_entry_from_dict(info_dict, "genres")
                        ]
                    ),
                    "release_date": get_entry_from_dict(
                        get_entry_from_dict(info_dict, "release_date"), "date"
                    ),
                    "num_reviews": get_entry_from_dict(reviews_dict, "num_reviews"),
                    "review_score": get_entry_from_dict(reviews_dict, "review_score"),
                    "review_score_desc": get_entry_from_dict(
                        reviews_dict, "review_score_desc"
                    ),
                    "total_positive": get_entry_from_dict(
                        reviews_dict, "total_positive"
                    ),
                    "total_negative": get_entry_from_dict(
                        reviews_dict, "total_negative"
                    ),
                    "total_reviews": get_entry_from_dict(reviews_dict, "total_reviews"),
                }

                logger.debug(game_dict)
                game_dict_list.append(game_dict)

                if separate_export:
                    # have to put the dict in a list for some reason
                    df = pd.DataFrame([game_dict], index=[0])
                    if game_dict.get("name"):
                        filename = f"Exports/{game_id}_{slugify(game_dict['name'])}.csv"
                    else:
                        filename = f"Exports/{game_id}.csv"
                    if not Path(filename).is_file():
                        logger.debug("Writing new file %s", filename)
                        with open(filename, "w") as f:
                            df.to_csv(f, sep="\t", index=False)
                    else:
                        logger.debug("Writing file %s", filename)
                        with open(filename, "a") as f:
                            df.to_csv(f, sep="\t", header=False, index=False)

    df = pd.DataFrame(game_dict_list)

    logger.debug("Writing complete export game_info.csv")

    filename = "Exports/game_info.csv"
    if not Path(filename).is_file():
        df.to_csv(filename, sep="\t", index=False)
    else:
        with open(filename, "a") as f:
            df.to_csv(f, sep="\t", index=False, header=False)
    logger.info("Runtime : %.2f seconds" % (time.time() - temps_debut))


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
    parser.add_argument(
        "-s",
        "--separate_export",
        help="Export separately (one file per game + the global file)",
        dest="separate_export",
        action="store_true",
    )
    parser.set_defaults(boolean_flag=False, separate_export=False)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
