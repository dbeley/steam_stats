import os
import logging
import time
import argparse
import configparser
import csv
import requests
import pandas as pd
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
    dict_games = []
    url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?steamid={user_id}"
    logger.info("Fetching page %s.", url)
    json_dict = requests.get(url).json()
    logger.debug(f"get_wishlist_ids JSON output: {json_dict}")
    if json_dict:
        for game_data in json_dict["response"]["items"]:
            dict_games.append({"appid": game_data["appid"]})
    return dict_games


def main():
    args = parse_args()
    if not args.type:
        raise ValueError("-t/--type argument required. Exiting.")
    elif args.type not in ["all", "owned", "wishlist", "both"]:
        raise ValueError("Type %s not supported. Exiting.", args.type)

    config = configparser.ConfigParser()
    try:
        config.read("config.ini")
    except Exception:
        raise FileNotFoundError(
            "No config file found. Be sure you have a config.ini file."
        )
    try:
        api_key = os.environ.get("STEAM_API_KEY")
        if not api_key:
            api_key = config["steam"]["api_key"]
    except Exception:
        raise ValueError("No api_key found. Check your config file.")

    if args.user_id:
        user_id = args.user_id
    else:
        try:
            user_id = os.environ.get("STEAM_USER_ID")
            if not user_id:
                user_id = config["steam"]["user_id"]
        except Exception:
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
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
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
        help="User id to extract the games data from (steamID64). Default : user in config.ini",
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
