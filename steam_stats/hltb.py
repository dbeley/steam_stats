import logging
from howlongtobeatpy import HowLongToBeat

logger = logging.getLogger(__name__)


def clean_howlongtobeat_entry(entry):
    if str(entry) == "-1":
        return None
    else:
        return str(entry).replace("½", ".5")


def get_howlongtobeat_infos(search):
    result = HowLongToBeat().search(search)
    if result:
        return {
            "howlongtobeat_url": result[0].game_web_link,
            "howlongtobeat_main": clean_howlongtobeat_entry(result[0].gameplay_main),
            "howlongtobeat_main_unit": result[0].gameplay_main_unit,
            "howlongtobeat_main_extra": clean_howlongtobeat_entry(
                result[0].gameplay_main_extra
            ),
            "howlongtobeat_main_extra_unit": result[0].gameplay_main_extra_unit,
            "howlongtobeat_completionist": clean_howlongtobeat_entry(
                result[0].gameplay_completionist
            ),
            "howlongtobeat_completionist_unit": result[0].gameplay_completionist_unit,
        }
    return None
