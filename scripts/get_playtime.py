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


def get_playtime_recent(api_key, user_id):
    url_recent = (
        "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"
        f"?key={api_key}&steamid={user_id}"
    )
    json_dict_recent = requests.get(url_recent).json()
    games_list_recent = []
    for game in json_dict_recent["response"]["games"]:
        games_list_recent.append(
            {
                "appid": game["appid"],
                "playtime_2weeks": int(game["playtime_2weeks"]),
            }
        )
    return games_list_recent


def get_playtime(api_key, user_id):
    url = (
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={api_key}&steamid={user_id}&format=json&include_played_free_games=1"
    )
    json_dict = requests.get(url).json()
    games_list = []
    for game in json_dict["response"]["games"]:
        games_list.append(
            {
                "appid": game["appid"],
                "playtime": game["playtime_forever"],
                "playtime_windows": game["playtime_windows_forever"],
                "playtime_mac": game["playtime_mac_forever"],
                "playtime_linux": game["playtime_linux_forever"],
            }
        )
    return games_list


def main():
    args = parse_args()

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

    dict_games = get_playtime(api_key, user_id)
    dict_games_recent = get_playtime_recent(api_key, user_id)

    df = pd.DataFrame(dict_games)
    df_recent = pd.DataFrame(dict_games_recent)
    df = pd.merge(df, df_recent, how="left", on=["appid"])
    df["playtime_2weeks"] = df["playtime_2weeks"].fillna(0.0).astype(int)
    filename = args.filename if args.filename else f"Exports/playtime_{user_id}.csv"
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info(f"Output file: {filename}.")

    logger.info("Runtime : %.2f seconds." % (time.time() - temps_debut))


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
