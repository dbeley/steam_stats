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
import re
from pathlib import Path

logger = logging.getLogger()
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
temps_debut = time.time()


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def main():
    args = parse_args()
    file = args.file
    separate_export = args.separate_export

    if not file:
        logger.error("-f/--file argument not filled. Exiting.")
        exit()

    if not Path(file).is_file():
        logger.error(f"{file} is not a file. Exiting.")
        exit()

    logger.debug("Reading config file")
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        api_key = config['steam']['api_key']
    except Exception as e:
        logger.error("Problem with the config file.")
        exit()

    logger.debug("Reading CSV file")
    df = pd.read_csv(file, sep='\t|;', engine='python')
    logger.debug(f"Columns : {df.columns}")

    ids = df.appid.tolist()

    Path("Exports").mkdir(parents=True, exist_ok=True)

    game_dict_list = []
    for game_id in ids:
        game_dict = {}
        auj = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        game_dict['export_date'] = auj
        game_dict['appid'] = game_id

        try:
            url_info_game = f"http://store.steampowered.com/api/appdetails?appids={game_id}"
            info_dict = requests.get(url_info_game).json()
            info_dict = info_dict[str(game_id)]['data']

            game_dict['name'] = info_dict['name'].strip()
            game_dict['type'] = info_dict['type']
            game_dict['required_age'] = info_dict['required_age']
            game_dict['is_free'] = info_dict['is_free']
            game_dict['developers'] = info_dict['developers']
            game_dict['publishers'] = info_dict['publishers']
            game_dict['windows'] = info_dict['platforms']['windows']
            game_dict['linux'] = info_dict['platforms']['linux']
            game_dict['mac'] = info_dict['platforms']['mac']
            game_dict['genres'] = info_dict['genres']
            game_dict['release_date'] = info_dict['release_date']['date']
            logger.debug(f"Game {game_dict['name']} - ID {game_id} : {url_info_game}")
        except Exception as e:
            logger.error(f"ID {game_id} - {url_info_game} : {e}")

        try:
            url_reviews = f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
            reviews_dict = requests.get(url_reviews).json()
            reviews_dict = reviews_dict['query_summary']

            game_dict['num_reviews'] = reviews_dict['num_reviews']
            game_dict['review_score'] = reviews_dict['review_score']
            game_dict['review_score_desc'] = reviews_dict['review_score_desc']
            game_dict['total_positive'] = reviews_dict['total_positive']
            game_dict['total_negative'] = reviews_dict['total_negative']
            game_dict['total_reviews'] = reviews_dict['total_reviews']
        except Exception as e:
            logger.debug(f"url_reviews - {url_reviews} : {e}")

        game_dict_list.append(game_dict)

        logger.debug(f"{game_dict}")
        if separate_export:
            # have to put the dict in a list for some reason
            df = pd.DataFrame([game_dict], index=[0])
            if game_dict.get('name'):
                filename = f"Exports/{game_id}_{slugify(game_dict['name'])}.csv"
            else:
                filename = f"Exports/{game_id}.csv"
            if not Path(filename).is_file():
                logger.debug(f"Writing new file {filename}")
                with open(filename, 'w') as f:
                    df.to_csv(f, sep='\t', index=False)
            else:
                logger.debug(f"Writing file {filename}")
                with open(filename, 'a') as f:
                    df.to_csv(f, sep='\t', header=False, index=False)

    df = pd.DataFrame(game_dict_list)

    df.to_csv("Exports/game_info.csv", sep='\t', index=False)
    logger.info("Runtime : %.2f seconds" % (time.time() - temps_debut))


def parse_args():
    parser = argparse.ArgumentParser(description='Steam script')
    parser.add_argument('--debug', help="Display debugging information", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('-f', '--file', help="File containing the ids to parse", type=str)
    parser.add_argument('-s', '--separate_export', help="Export separately (one file per game + the global file)", dest="separate_export", action='store_true')
    parser.set_defaults(boolean_flag=False, separate_export=False)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == '__main__':
    main()
