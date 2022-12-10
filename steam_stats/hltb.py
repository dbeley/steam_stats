import logging
from howlongtobeatpy import HowLongToBeat

logger = logging.getLogger(__name__)


def clean_howlongtobeat_entry(entry):
    if str(entry) == "-1" or str(entry) == "0":
        return None
    return str(entry).replace("½", ".5")


def get_howlongtobeat_infos(search):
    result = HowLongToBeat().search(search)
    if result:
        return {
            "howlongtobeat_url": result[0].game_web_link,
            "howlongtobeat_main": clean_howlongtobeat_entry(result[0].main_story),
            "howlongtobeat_main_extra": clean_howlongtobeat_entry(result[0].main_extra),
            "howlongtobeat_completionist": clean_howlongtobeat_entry(
                result[0].completionist
            ),
        }
    return None
