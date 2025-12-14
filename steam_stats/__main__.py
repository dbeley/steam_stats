import logging
import time
import argparse
import datetime
import json
import urllib.parse
import pandas as pd
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
from tqdm import tqdm
from .config import SteamConfig
from .itad import get_itad_data
from .requests import get_steam_json

logger = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
START_TIME = time.time()
BATCH_SIZE = 200  # Optimized request allows 200 games per batch


def get_achievements_dict(s, api_key, user_id, app_id):
    url_achievements = (
        "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
        f"?appid={app_id}&key={api_key}&steamid={user_id}"
    )
    result = get_steam_json(s, url_achievements, app_id)
    if "error" in result["playerstats"].keys():
        if result["playerstats"]["error"] == "Requested app has no stats":
            return {}
        logger.warning(
            "Unexpected error for appid %s: %s", app_id, result["playerstats"]["error"]
        )
        return {}
    return {
        "appid": app_id,
        "achieved": sum(
            [
                achievement["achieved"] == 1
                for achievement in result["playerstats"]["achievements"]
            ]
        )
        if "achievements" in result["playerstats"].keys()
        else None,
        "total_achievements": len(result["playerstats"]["achievements"])
        if "achievements" in result["playerstats"].keys()
        else None,
    }


def get_data_dict(s, game_id: str) -> dict[str, str]:
    """Legacy function for single game fetching. Replaced by get_games_batch."""
    url_game = f"http://store.steampowered.com/api/appdetails?appids={game_id}"
    result = get_steam_json(s, url_game, game_id)
    game_result = result[str(game_id)]
    if success := game_result.get("success"):
        logger.debug("ID %s - success : %s", game_id, success)
        data_dict = game_result["data"]
        return data_dict
    else:
        logger.warning(
            "Couldn't extract data for game %s: %s",
            game_id,
            game_result,
        )
        return {}


def get_games_batch(s, appids: list[str]) -> dict[str, dict]:
    """
    Fetch game details for multiple games using IStoreBrowseService/GetItems API.
    Returns a dict mapping appid -> game data.

    Note: Only requests essential fields to keep URL length manageable.
    """
    request_json = {
        "ids": [{"appid": int(appid)} for appid in appids],
        "context": {"language": "english", "country_code": "US", "steam_realm": 1},
        "data_request": {
            "include_release": True,
            "include_platforms": True,
            "include_basic_info": True,
            "include_tag_count": 20,
            "include_reviews": True,
        },
    }

    encoded_json_string = urllib.parse.quote(json.dumps(request_json))
    url = f"https://api.steampowered.com/IStoreBrowseService/GetItems/v1?input_json={encoded_json_string}"

    try:
        result = s.get(url)
        result.raise_for_status()
        data = result.json()

        # Build a dict mapping appid -> store_item
        games_dict = {}
        if "response" in data and "store_items" in data["response"]:
            for store_item in data["response"]["store_items"]:
                appid = str(store_item.get("appid", ""))
                if appid:
                    games_dict[appid] = store_item

        return games_dict
    except Exception as e:
        logger.error("Error fetching batch of games: %s", e)
        return {}


def extract_game_data_from_store_item(store_item: dict) -> dict:
    """
    Extract game data from the new API format (IStoreBrowseService/GetItems).
    Maps fields from the new API to the format expected by the rest of the code.
    """
    import datetime

    # Map numeric type to string (0 = game, 1 = dlc, 2 = demo, etc.)
    type_map = {0: "game", 1: "dlc", 2: "demo", 3: "mod", 4: "video"}
    numeric_type = store_item.get("type", 0)
    type_str = type_map.get(numeric_type, "game")

    # Convert Unix timestamp to formatted date string
    release_timestamp = store_item.get("release", {}).get("steam_release_date", 0)
    if (
        release_timestamp
        and isinstance(release_timestamp, int)
        and release_timestamp > 0
    ):
        try:
            release_date_formatted = datetime.datetime.fromtimestamp(
                release_timestamp
            ).strftime("%b %d, %Y")
        except (ValueError, OSError):
            release_date_formatted = ""
    else:
        release_date_formatted = ""

    # Extract developers and publishers in the expected format
    developers_list = [
        {"name": dev.get("name", "")}
        for dev in store_item.get("basic_info", {}).get("developers", [])
    ]

    publishers_list = [
        {"name": pub.get("name", "")}
        for pub in store_item.get("basic_info", {}).get("publishers", [])
    ]

    # Extract genres/tags - filter out empty names
    tags = store_item.get("tags", [])
    genres_list = [
        {"description": tag.get("name", "")}
        for tag in tags
        if tag.get("name", "").strip()
    ]

    return {
        "name": store_item.get("name", ""),
        "appid": store_item.get("appid", ""),
        "type": type_str,
        "required_age": store_item.get("basic_info", {})
        .get("content_rating", {})
        .get("required_age", 0),
        "is_free": store_item.get("is_free", False),
        "developers": developers_list,
        "publishers": publishers_list,
        "platforms": {
            "windows": store_item.get("platforms", {}).get("windows", False),
            "linux": store_item.get("platforms", {}).get("steamos_linux", False),
            "mac": store_item.get("platforms", {}).get("mac", False),
        },
        "genres": genres_list,
        "release_date": {"date": release_date_formatted},
    }


def get_reviews_dict(s, game_id):
    url_reviews = (
        f"https://store.steampowered.com/appreviews/{game_id}?json=1&language=all"
    )
    result = get_steam_json(s, url_reviews, game_id)
    reviews_dict = result["query_summary"]
    return reviews_dict


# Config reading is now handled by the SteamConfig class in config.py


def main():
    args = parse_args()
    export_date = datetime.datetime.now().strftime("%Y-%m-%d")
    export_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not args.file:
        raise ValueError("-f/--file argument not filled. Exiting.")
    if not Path(args.file).is_file():
        raise FileNotFoundError("%s is not a file. Exiting.", args.file)

    config = SteamConfig()
    api_key = config.get_api_key()
    user_id = config.get_user_id()

    logger.debug("Reading CSV file")
    df = pd.read_csv(args.file, sep="\t|;", engine="python")
    logger.debug("Columns : %s", df.columns)

    ids = df.appid.tolist()
    Path("Exports").mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))

    game_dict_list = []

    # Split IDs into batches for the new API
    batches = [ids[i : i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]
    logger.info("Processing %d games in %d batches", len(ids), len(batches))

    for batch in tqdm(batches, desc="Batches", dynamic_ncols=True):
        # Fetch batch of games using the new API
        games_data = get_games_batch(s, batch)

        # Process each game in the batch
        for game_id in tqdm(
            batch, desc="Games in batch", leave=False, dynamic_ncols=True
        ):
            game_id = str(game_id)

            # Get game data from the batch result, or fall back to old API
            if game_id not in games_data:
                logger.warning(
                    "Game %s not found in batch response, trying old API", game_id
                )
                data_dict = get_data_dict(s, game_id)
                if not data_dict:
                    continue
                # For old API, reviews need to be fetched separately
                reviews_dict = get_reviews_dict(s, game_id)
            else:
                store_item = games_data[game_id]
                data_dict = extract_game_data_from_store_item(store_item)

                # Get reviews from the new API response
                reviews_summary = store_item.get("reviews", {}).get(
                    "summary_filtered", {}
                )

                # If reviews are not available in the new API, fall back to old endpoint
                if not reviews_summary or not reviews_summary.get("review_count"):
                    reviews_dict = get_reviews_dict(s, game_id)
                else:
                    # Use reviews from the new API
                    review_count = reviews_summary.get("review_count", 0)
                    percent_positive = reviews_summary.get("percent_positive", 0)

                    # Calculate positive/negative counts from percentage
                    # The new API provides percent_positive instead of raw counts
                    if review_count and percent_positive:
                        total_positive = int((percent_positive / 100) * review_count)
                        total_negative = review_count - total_positive
                    else:
                        total_positive = 0
                        total_negative = 0

                    reviews_dict = {
                        "num_reviews": review_count,
                        "review_score": percent_positive,
                        "review_score_desc": reviews_summary.get(
                            "review_score_label", ""
                        ),
                        "total_positive": total_positive,
                        "total_negative": total_negative,
                        "total_reviews": review_count,
                    }

            if not data_dict.get("name"):
                logger.warning("No name found for game %s, skipping", game_id)
                continue

            achievements_dict = get_achievements_dict(s, api_key, user_id, game_id)

            # Calculate achievement percentage
            achieved = achievements_dict.get("achieved")
            total_achievements = achievements_dict.get("total_achievements")
            if achieved is not None and total_achievements and total_achievements > 0:
                achievement_percentage = round((achieved / total_achievements) * 100, 1)
            else:
                achievement_percentage = None

            game_dict = {
                "export_date": export_time,
                "name": data_dict["name"].strip(),
                "appid": game_id,
                "type": data_dict.get("type"),
                "required_age": data_dict.get("required_age"),
                "is_free": data_dict.get("is_free"),
                "developers": ", ".join(
                    [dev.get("name", "") for dev in data_dict.get("developers", [])]
                ),
                "publishers": ", ".join(
                    [pub.get("name", "") for pub in data_dict.get("publishers", [])]
                ),
                "windows": data_dict["platforms"]["windows"],
                "linux": data_dict["platforms"]["linux"],
                "mac": data_dict["platforms"]["mac"],
                "genres": ", ".join(
                    [x["description"] for x in data_dict.get("genres", [])]
                ),
                "release_date": data_dict["release_date"]["date"],
                "num_reviews": reviews_dict.get("num_reviews"),
                "review_score": reviews_dict.get("review_score"),
                "review_score_desc": reviews_dict.get("review_score_desc"),
                "total_positive": reviews_dict.get("total_positive"),
                "total_negative": reviews_dict.get("total_negative"),
                "total_reviews": reviews_dict.get("total_reviews"),
                "url": f"https://store.steampowered.com/app/{game_id}",
                "achieved_achievements": achieved,
                "total_achievements": total_achievements,
                "achievement_percentage": achievement_percentage,
            }

            if args.export_extra_data:
                itad_api_key = config.get_itad_api_key()
                result_itad = get_itad_data(s, itad_api_key, game_id)
                if result_itad:
                    game_dict = {**game_dict, **result_itad}

            logger.debug("Result for game %s: %s.", game_id, game_dict)
            game_dict_list.append(game_dict)

    df = pd.DataFrame(game_dict_list)
    df = df.astype(
        {
            "achieved_achievements": "Int64",
            "total_achievements": "Int64",
            "total_positive": "Int64",
            "total_negative": "Int64",
            "total_reviews": "Int64",
        }
    )

    filename = (
        args.export_filename
        if args.export_filename
        else f"Exports/game_info_{export_date}.csv"
    )
    logger.debug("Writing complete export %s.", filename)
    df.to_csv(filename, sep="\t", index=False)
    logger.info("Runtime : %.2f seconds" % (time.time() - START_TIME))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Steam games data from a list of appids"
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
        "-f", "--file", help="File containing the appids to parse", type=str
    )
    parser.add_argument("--export_filename", help="Override export filename", type=str)
    parser.add_argument(
        "--export_extra_data",
        help="Enable extra data fetching (ITAD)",
        dest="export_extra_data",
        action="store_true",
    )
    parser.set_defaults(export_extra_data=False)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
