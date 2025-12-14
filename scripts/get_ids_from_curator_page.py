import logging
import time
import argparse
import csv
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

logger = logging.getLogger()
start_time = time.time()


def read_soup_from_fs(filename: str):
    with open(filename, "r") as f:
        content = f.read()
    return BeautifulSoup(content, "html.parser")


def get_soup(url: str):
    return BeautifulSoup(requests.get(url).content, "lxml")


def get_id_from_link(link: str):
    return link.split("/")[4]


def get_curator_ids(soup):
    list_items = []
    for item in soup.find("div", {"id": "RecommendationsRows"}).find_all(
        "div", {"class": "recommendation"}
    ):
        try:
            link = item.find("a")["href"]
            list_items.append({"appid": get_id_from_link(link)})
        except Exception as e:
            logger.warning("Couldn't extract game ID from curator item: %s", e)
            continue
    return list_items


def main():
    args = parse_args()

    logger.debug("Reading HTML file")
    soup = read_soup_from_fs(args.filename)
    dict_games = get_curator_ids(soup)

    Path("Exports").mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(dict_games)
    filename = f"Exports/ids_curators_{start_time}.csv"
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info(f"Output file: {filename}.")

    logger.info("Runtime : %.2f seconds." % (time.time() - start_time))


def parse_args():
    parser = argparse.ArgumentParser(
        description="export ids of a curation page (html export)"
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
        "-f",
        "--filename",
        help="File containing html data for curator",
        type=str,
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
