import logging
import time
import argparse
import configparser
import requests
import re
import unicodedata
import pandas as pd
from pathlib import Path

logger = logging.getLogger()
temps_debut = time.time()


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


def get_all_ids(api_key):
    url = f"http://api.steampowered.com/ISteamApps/GetAppList/v0002/?key={api_key}&format=json"
    json_dict = requests.get(url).json()
    dict_games = []
    for game in json_dict["applist"]["apps"]:
        dict_game = {}
        dict_game["appid"] = game["appid"]
        dict_games.append(dict_game)
    return dict_games


def get_owned_ids(api_key, user_id):
    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={user_id}&format=json"
    json_dict = requests.get(url).json()
    dict_games = []
    for game in json_dict["response"]["games"]:
        dict_game = {}
        dict_game["appid"] = game["appid"]
        dict_games.append(dict_game)
    return dict_games


def get_wishlist_ids(user_id):
    page = 0
    dict_games = []
    while True:
        url = f"https://store.steampowered.com/wishlist/profiles/{user_id}/wishlistdata/?p={page}"
        page += 1
        logger.info("Fetching page %s.", url)
        json_dict = requests.get(url).json()
        if json_dict:
            for game_id in json_dict:
                dict_game = {}
                dict_game["appid"] = game_id
                dict_games.append(dict_game)
        else:
            break
    return dict_games


def main():
    args = parse_args()
    if not args.type:
        logger.error("-t/--type argument required. Exiting.")
        exit()
    elif args.type not in ["all", "owned", "wishlist", "both"]:
        logger.error("Type %s not supported. Exiting.", args.type)
        exit()

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    try:
        config.read("config.ini")
    except Exception as e:
        logger.error("No config file found. Be sure you have a config.ini file.")
        exit()
    try:
        api_key = config["steam"]["api_key"]
    except Exception as e:
        logger.error("No api_key found. Check your config file.")
        exit()

    logger.debug("Reading user_id")
    if args.user_id:
        user_id = args.user_id
    else:
        try:
            user_id = config["steam"]["user_id"]
        except Exception as e:
            logger.error(
                "No user specified. Specify a user_id directive in your config file or use the -u/--user_id flag"
            )
            exit()

    Path("Exports").mkdir(parents=True, exist_ok=True)

    if args.type == "all":
        logger.debug("Type : all")
        dict_games = get_all_ids(api_key)
    elif args.type == "owned":
        logger.debug("Type : owned")
        dict_games = get_owned_ids(api_key, user_id)
    elif args.type == "wishlist":
        logger.debug("Type : wishlist")
        dict_games = get_wishlist_ids(user_id)
    elif args.type == "both":
        logger.debug("Type : both")
        dict_games = get_owned_ids(api_key, user_id)
        dict_games += get_wishlist_ids(user_id)

    df = pd.DataFrame(dict_games)
    filename = (
        args.filename if args.filename else f"Exports/ids_{args.type}_{user_id}.csv"
    )
    df.to_csv(filename, sep="\t", index=False)
    logger.info(f"Output file: {filename}.")

    logger.info("Runtime : %.2f seconds." % (time.time() - temps_debut))


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
        help="User id to extract the games info from (steamID64). Default : user in config.ini",
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
