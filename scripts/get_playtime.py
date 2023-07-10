import logging
import time
import argparse
import configparser
import requests
import pandas as pd
from pathlib import Path

logger = logging.getLogger()
temps_debut = time.time()


def get_playtime(api_key, user_id):
    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={user_id}&format=json"
    json_dict = requests.get(url).json()
    dict_games = []
    for game in json_dict["response"]["games"]:
        dict_games.append(
            {
                "appid": game["appid"],
                "playtime": game["playtime_forever"],
                "playtime windows": game["playtime_windows_forever"],
                "playtime mac": game["playtime_mac_forever"],
                "playtime linux": game["playtime_linux_forever"],
            }
        )
    return dict_games


def main():
    args = parse_args()

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    try:
        config.read("config.ini")
    except Exception:
        raise FileNotFoundError(
            "No config file found. Be sure you have a config.ini file."
        )
    try:
        api_key = config["steam"]["api_key"]
    except Exception:
        raise ValueError("No api_key found. Check your config file.")

    logger.debug("Reading user_id")
    if args.user_id:
        user_id = args.user_id
    else:
        try:
            user_id = config["steam"]["user_id"]
        except Exception:
            raise ValueError(
                "No user specified. Specify a user_id directive in your config file or use the -u/--user_id flag"
            )

    Path("Exports").mkdir(parents=True, exist_ok=True)

    dict_games = get_playtime(api_key, user_id)

    df = pd.DataFrame(dict_games)
    filename = args.filename if args.filename else f"Exports/playtime_{user_id}.csv"
    df.to_csv(filename, sep="\t", index=False)
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
