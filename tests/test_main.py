"""Tests for steam_stats.__main__ (data extraction helpers)."""

import re

import pytest
import requests

import steam_stats.__main__ as main_mod

# ---------------------------------------------------------------------------
# extract_game_data_from_store_item
# ---------------------------------------------------------------------------

FULL_STORE_ITEM = {
    "appid": 70,
    "name": "Half-Life",
    "type": 0,
    "is_free": False,
    "release": {"steam_release_date": 949300800},  # 2000-01-31 UTC
    "basic_info": {
        "developers": [{"name": "Valve"}],
        "publishers": [{"name": "Valve"}],
        "content_rating": {"required_age": 17},
    },
    "platforms": {"windows": True, "mac": True, "steamos_linux": False},
    "tags": [{"name": "FPS"}, {"name": "Action"}, {"name": ""}],
}


def test_extract_full_store_item():
    data = main_mod.extract_game_data_from_store_item(FULL_STORE_ITEM)
    assert data["name"] == "Half-Life"
    assert data["appid"] == 70
    assert data["type"] == "game"
    assert data["is_free"] is False
    assert data["required_age"] == 17
    assert data["developers"] == [{"name": "Valve"}]
    assert data["publishers"] == [{"name": "Valve"}]
    assert data["platforms"] == {"windows": True, "linux": False, "mac": True}
    assert data["genres"] == [{"description": "FPS"}, {"description": "Action"}]
    assert re.fullmatch(r"[A-Z][a-z]{2} \d{2}, \d{4}", data["release_date"]["date"])


def test_extract_missing_fields_use_defaults():
    data = main_mod.extract_game_data_from_store_item({"appid": 1, "name": "X"})
    assert data["type"] == "game"
    assert data["developers"] == []
    assert data["publishers"] == []
    assert data["genres"] == []
    assert data["release_date"]["date"] == ""
    assert data["platforms"] == {"windows": False, "linux": False, "mac": False}


def test_extract_type_mapping():
    assert main_mod.extract_game_data_from_store_item({"type": 1})["type"] == "dlc"
    assert main_mod.extract_game_data_from_store_item({"type": 2})["type"] == "demo"


def test_extract_zero_release_timestamp():
    data = main_mod.extract_game_data_from_store_item(
        {"release": {"steam_release_date": 0}}
    )
    assert data["release_date"]["date"] == ""


# ---------------------------------------------------------------------------
# get_achievements_dict
# ---------------------------------------------------------------------------


def test_get_achievements_counts(monkeypatch):
    monkeypatch.setattr(
        main_mod,
        "get_steam_json",
        lambda *a, **k: {
            "playerstats": {
                "achievements": [
                    {"achieved": 1},
                    {"achieved": 1},
                    {"achieved": 0},
                ]
            }
        },
    )
    result = main_mod.get_achievements_dict(None, "key", "user", "70")
    assert result == {"appid": "70", "achieved": 2, "total_achievements": 3}


def test_get_achievements_no_playerstats(monkeypatch):
    monkeypatch.setattr(main_mod, "get_steam_json", lambda *a, **k: {})
    assert main_mod.get_achievements_dict(None, "key", "user", "70") == {}


def test_get_achievements_no_stats_error(monkeypatch):
    monkeypatch.setattr(
        main_mod,
        "get_steam_json",
        lambda *a, **k: {"playerstats": {"error": "Requested app has no stats"}},
    )
    assert main_mod.get_achievements_dict(None, "key", "user", "70") == {}


def test_get_achievements_missing_list(monkeypatch):
    monkeypatch.setattr(main_mod, "get_steam_json", lambda *a, **k: {"playerstats": {}})
    assert main_mod.get_achievements_dict(None, "key", "user", "70") == {}


# ---------------------------------------------------------------------------
# get_games_batch
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(
        self, json_data=None, status_code=200, bad_json=False, http_error=None
    ):
        self._json_data = json_data
        self.status_code = status_code
        self._bad_json = bad_json
        self._http_error = http_error

    def raise_for_status(self):
        if self._http_error:
            raise self._http_error

    def json(self):
        if self._bad_json:
            raise requests.exceptions.JSONDecodeError("bad", "", 0)
        return self._json_data


class FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, url, timeout=None):
        return self._response


def test_get_games_batch_maps_appids():
    response = FakeResponse(
        json_data={
            "response": {
                "store_items": [
                    {"appid": 70, "name": "HL"},
                    {"appid": 80, "name": "Portal"},
                ]
            }
        }
    )
    result = main_mod.get_games_batch(FakeSession(response), ["70", "80"])
    assert set(result) == {"70", "80"}
    assert result["70"]["name"] == "HL"


def test_get_games_batch_empty_response():
    response = FakeResponse(json_data={"response": {}})
    assert main_mod.get_games_batch(FakeSession(response), ["70"]) == {}


def test_get_games_batch_bad_json_returns_empty():
    response = FakeResponse(bad_json=True)
    assert main_mod.get_games_batch(FakeSession(response), ["70"]) == {}


def test_get_games_batch_http_error_returns_empty():
    response = FakeResponse(http_error=requests.exceptions.ConnectionError("boom"))
    assert main_mod.get_games_batch(FakeSession(response), ["70"]) == {}


# ---------------------------------------------------------------------------
# process_single_game
# ---------------------------------------------------------------------------

STORE_ITEM_WITH_REVIEWS = {
    "appid": 70,
    "name": "Half-Life",
    "type": 0,
    "reviews": {
        "summary_filtered": {
            "review_count": 100,
            "percent_positive": 80,
            "review_score_label": "Very Positive",
        }
    },
}


class StubConfig:
    def get_itad_api_key(self):
        return "itad_key"


@pytest.fixture
def no_achievements(monkeypatch):
    monkeypatch.setattr(main_mod, "get_achievements_dict", lambda *a, **k: {})


def test_process_single_game_new_api_reviews(no_achievements):
    result = main_mod.process_single_game(
        None,
        "70",
        {"70": STORE_ITEM_WITH_REVIEWS},
        "key",
        "user",
        "2024-01-01 00:00",
        False,
        StubConfig(),
    )
    assert result["name"] == "Half-Life"
    assert result["appid"] == "70"
    assert result["num_reviews"] == 100
    assert result["total_positive"] == 80
    assert result["total_negative"] == 20
    assert result["total_reviews"] == 100
    assert result["url"] == "https://store.steampowered.com/app/70"


def test_process_single_game_missing_name_returns_none(no_achievements, monkeypatch):
    monkeypatch.setattr(main_mod, "get_reviews_dict", lambda *a, **k: {})
    item = {"appid": 70, "name": "", "type": 0}
    result = main_mod.process_single_game(
        None, "70", {"70": item}, "key", "user", "t", False, StubConfig()
    )
    assert result is None


def test_process_single_game_falls_back_to_reviews_endpoint(monkeypatch):
    monkeypatch.setattr(main_mod, "get_achievements_dict", lambda *a, **k: {})
    monkeypatch.setattr(
        main_mod,
        "get_reviews_dict",
        lambda *a, **k: {
            "num_reviews": 50,
            "review_score": 9,
            "review_score_desc": "Overwhelmingly Positive",
            "total_positive": 45,
            "total_negative": 5,
            "total_reviews": 50,
        },
    )
    item = {"appid": 70, "name": "Half-Life", "type": 0, "reviews": {}}
    result = main_mod.process_single_game(
        None, "70", {"70": item}, "key", "user", "t", False, StubConfig()
    )
    assert result["total_positive"] == 45


def test_process_single_game_achievements(monkeypatch):
    monkeypatch.setattr(
        main_mod,
        "get_achievements_dict",
        lambda *a, **k: {"appid": "70", "achieved": 3, "total_achievements": 4},
    )
    result = main_mod.process_single_game(
        None,
        "70",
        {"70": STORE_ITEM_WITH_REVIEWS},
        "key",
        "user",
        "t",
        False,
        StubConfig(),
    )
    assert result["achieved_achievements"] == 3
    assert result["total_achievements"] == 4
    assert result["achievement_percentage"] == 75.0


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["steam_stats", "-f", "games.csv"])
    args = main_mod.parse_args()
    assert args.file == "games.csv"
    assert args.workers == 10
    assert args.deduplicate is False
    assert args.export_extra_data is False
    assert args.export_json is False


def test_parse_args_flags(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "steam_stats",
            "-f",
            "g.csv",
            "--export_json",
            "--deduplicate",
            "--workers",
            "4",
        ],
    )
    args = main_mod.parse_args()
    assert args.export_json is True
    assert args.deduplicate is True
    assert args.workers == 4


def test_parse_args_rejects_non_positive_workers(monkeypatch):
    monkeypatch.setattr("sys.argv", ["steam_stats", "-f", "g.csv", "--workers", "0"])
    with pytest.raises(SystemExit):
        main_mod.parse_args()


# ---------------------------------------------------------------------------
# release dates use UTC
# ---------------------------------------------------------------------------


def test_release_date_uses_utc():
    data = main_mod.extract_game_data_from_store_item(
        {"release": {"steam_release_date": 949300800}}
    )
    assert data["release_date"]["date"] == "Jan 31, 2000"


# ---------------------------------------------------------------------------
# normalise_query_summary / get_reviews_dict
# ---------------------------------------------------------------------------


LIVE_QUERY_SUMMARY = {
    "num_reviews": 0,
    "review_score": 9,
    "review_score_desc": "Overwhelmingly Positive",
    "total_positive": 113503,
    "total_negative": 3974,
    "total_reviews": 117477,
}


def test_normalise_query_summary_converts_scale_to_percentage():
    result = main_mod.normalise_query_summary(LIVE_QUERY_SUMMARY)
    assert result["review_score"] == 97
    assert result["review_score_desc"] == "Overwhelmingly Positive"
    assert result["total_positive"] == 113503
    assert result["total_negative"] == 3974
    assert result["total_reviews"] == 117477


def test_normalise_query_summary_without_counts():
    result = main_mod.normalise_query_summary({"num_reviews": 5})
    assert result["review_score"] is None


def test_get_reviews_dict_normalises(monkeypatch):
    monkeypatch.setattr(
        main_mod,
        "get_steam_json",
        lambda *a, **k: {"query_summary": dict(LIVE_QUERY_SUMMARY)},
    )
    result = main_mod.get_reviews_dict(None, "70")
    assert result["review_score"] == 97


def test_get_reviews_dict_no_summary(monkeypatch):
    monkeypatch.setattr(main_mod, "get_steam_json", lambda *a, **k: {})
    assert main_mod.get_reviews_dict(None, "70") == {}


# ---------------------------------------------------------------------------
# read_appids / build_dataframe
# ---------------------------------------------------------------------------


def test_read_appids(tmp_path):
    path = tmp_path / "games.csv"
    path.write_text("name\tappid\nHalf-Life\t70\nPortal\t220\n")
    assert main_mod.read_appids(str(path)) == ["70", "220"]


def test_read_appids_keeps_integer_format(tmp_path):
    path = tmp_path / "games.csv"
    path.write_text("appid\n70\n")
    assert main_mod.read_appids(str(path)) == ["70"]


def test_read_appids_drops_missing_values(tmp_path):
    path = tmp_path / "games.csv"
    path.write_text("name\tappid\nHalf-Life\t70\nNoId\t\n")
    assert main_mod.read_appids(str(path)) == ["70"]


def test_read_appids_missing_column_raises(tmp_path):
    path = tmp_path / "games.csv"
    path.write_text("name\tsomething\nHalf-Life\t70\n")
    with pytest.raises(ValueError, match="No 'appid' column"):
        main_mod.read_appids(str(path))


def test_build_dataframe_empty_does_not_crash():
    df = main_mod.build_dataframe([])
    assert len(df) == 0
    for column in main_mod.INT_COLUMNS:
        assert column in df.columns
        assert str(df[column].dtype) == "Int64"


def test_build_dataframe_casts_integers():
    rows = [
        {
            "name": "Half-Life",
            "appid": "70",
            "total_positive": 45,
            "total_negative": 5,
            "total_reviews": 50,
            "achieved_achievements": None,
            "total_achievements": None,
        }
    ]
    df = main_mod.build_dataframe(rows)
    assert str(df["total_positive"].dtype) == "Int64"
    assert df["total_positive"].iloc[0] == 45
