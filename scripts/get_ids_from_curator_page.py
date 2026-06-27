import logging
import time
import argparse
import csv
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

logger = logging.getLogger()
START_TIME = time.time()


def read_soup_from_fs(filename: str):
    if not Path(filename).is_file():
        raise FileNotFoundError(f"{filename} is not a valid file.")
    with open(filename, "r") as f:
        content = f.read()
    return BeautifulSoup(content, "html.parser")


def get_soup(url: str):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "lxml")
    except requests.exceptions.RequestException as e:
        logger.error("Failed to fetch URL %s: %s", url, e)
        return None


def get_id_from_link(link: str):
    parts = link.split("/")
    return parts[4] if len(parts) > 4 else parts[-1]


def get_curator_ids(soup):
    list_items = []
    recommendations_rows = soup.find("div", {"id": "RecommendationsRows"})
    if not recommendations_rows:
        logger.warning("Could not find RecommendationsRows div in the page")
        return list_items

    for item in recommendations_rows.find_all("div", {"class": "recommendation"}):
        try:
            link_tag = item.find("a")
            if not link_tag or not link_tag.get("href"):
                continue
            link = link_tag["href"]
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

    if not dict_games:
        logger.warning("No games found in curator page.")
        return

    Path("Exports").mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(dict_games)
    filename = f"Exports/ids_curators_{int(START_TIME)}.csv"
    df.to_csv(filename, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.info("Output file: %s.", filename)

    logger.info("Runtime : %.2f seconds.", time.time() - START_TIME)


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
