import logging
import time
import argparse
import configparser
import requests
import re
import unicodedata
import pandas as pd
import json
from pathlib import Path

logger = logging.getLogger()
temps_debut = time.time()


def get_all_ids(api_key):
    url = f"http://api.steampowered.com/ISteamApps/GetAppList/v0002/?key={api_key}&format=json"
    json_dict = requests.get(url).json()
    logger.debug(f"get_all_ids JSON output: {json_dict}")
    dict_games = []
    for game in json_dict["applist"]["apps"]:
        dict_games.append({"appid": game["appid"]})
    return dict_games


def get_owned_ids(api_key, user_id):
    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={user_id}&format=json"
    json_dict = requests.get(url).json()
    logger.debug(f"get_owned_ids JSON output: {json_dict}")
    dict_games = []
    for game in json_dict["response"]["games"]:
        dict_games.append({"appid": game["appid"]})
    return dict_games


def get_wishlist_ids(user_id):
    page = 0
    dict_games = []
    while True:
        url = f"https://store.steampowered.com/wishlist/profiles/{user_id}/wishlistdata/?p={page}"
        page += 1
        logger.info("Fetching page %s.", url)
        json_dict = requests.get(url).json()
        logger.debug(f"get_wishlist_ids JSON output: {json_dict}")
        if json_dict:
            for game_id in json_dict:
                dict_games.append({"appid": game_id})
        else:
            break
    return dict_games


def main():
    args = parse_args()
    if not args.type:
        raise ValueError("-t/--type argument required. Exiting.")
    elif args.type not in ["all", "owned", "wishlist", "both"]:
        raise ValueError("Type %s not supported. Exiting.", args.type)

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    try:
        config.read("config.ini")
    except Exception as e:
        raise FileNotFoundError(
            "No config file found. Be sure you have a config.ini file."
        )
    try:
        api_key = config["steam"]["api_key"]
    except Exception as e:
        raise ValueError("No api_key found. Check your config file.")

    logger.debug("Reading user_id")
    if args.user_id:
        user_id = args.user_id
    else:
        try:
            user_id = config["steam"]["user_id"]
        except Exception as e:
            raise ValueError(
                "No user specified. Specify a user_id directive in your config file or use the -u/--user_id flag"
            )

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
