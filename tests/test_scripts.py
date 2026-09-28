"""Tests for the standalone scripts in scripts/."""

import diff_two_lists
import get_ids
import get_ids_from_curator_page as curator
import get_playtime
import pandas as pd
import pytest
import requests


class FakeResponse:
    def __init__(self, json_data=None, status_code=200, http_error=None):
        self._json_data = json_data
        self.status_code = status_code
        self._http_error = http_error

    def raise_for_status(self):
        if self._http_error:
            raise self._http_error

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, url, timeout=None):
        return self._response


# ---------------------------------------------------------------------------
# diff_two_lists
# ---------------------------------------------------------------------------


def test_read_from_file(tmp_path):
    path = tmp_path / "list.txt"
    path.write_text("70\n80\n90\n")
    assert diff_two_lists.read_from_file(str(path)) == ["70", "80", "90"]


def test_read_from_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        diff_two_lists.read_from_file(str(tmp_path / "nope.txt"))


def test_read_field_from_csv(tmp_path):
    path = tmp_path / "data.csv"
    pd.DataFrame({"appid": [70, 80], "name": ["a", "b"]}).to_csv(
        path, sep="\t", index=False
    )
    assert diff_two_lists.read_field_from_file(str(path), "appid", 1) == ["70", "80"]


def test_read_field_unsupported_type_raises(tmp_path):
    path = tmp_path / "data.xyz"
    path.write_text("a")
    with pytest.raises(ValueError):
        diff_two_lists.read_field_from_file(str(path), "appid", 1)


# ---------------------------------------------------------------------------
# get_ids
# ---------------------------------------------------------------------------


def test_get_id_from_link():
    assert (
        curator.get_id_from_link("https://store.steampowered.com/app/70/HalfLife/")
        == "70"
    )


def test_get_curator_ids():
    html = """
    <div id="RecommendationsRows">
      <div class="recommendation">
        <a href="https://store.steampowered.com/app/70/HalfLife/">HL</a>
      </div>
      <div class="recommendation">
        <a href="https://store.steampowered.com/app/220/Portal/">Portal</a>
      </div>
      <div class="recommendation"><span>no link</span></div>
    </div>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    assert curator.get_curator_ids(soup) == [{"appid": "70"}, {"appid": "220"}]


def test_get_curator_ids_missing_container():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html></html>", "html.parser")
    assert curator.get_curator_ids(soup) == []


def test_get_all_ids(monkeypatch):
    response = FakeResponse(
        json_data={"applist": {"apps": [{"appid": 70, "name": "HL"}, {"appid": 80}]}}
    )
    monkeypatch.setattr(get_ids, "create_session", lambda: FakeSession(response))
    assert get_ids.get_all_ids("key") == [{"appid": 70}, {"appid": 80}]


def test_get_all_ids_http_error_returns_empty(monkeypatch):
    response = FakeResponse(http_error=requests.exceptions.ConnectionError("boom"))
    monkeypatch.setattr(get_ids, "create_session", lambda: FakeSession(response))
    assert get_ids.get_all_ids("key") == []


def test_get_owned_ids(monkeypatch):
    response = FakeResponse(
        json_data={"response": {"games": [{"appid": 70, "playtime_forever": 5}]}}
    )
    monkeypatch.setattr(get_ids, "create_session", lambda: FakeSession(response))
    assert get_ids.get_owned_ids("key", "user") == [{"appid": 70}]


def test_get_wishlist_ids(monkeypatch):
    response = FakeResponse(json_data={"response": {"items": [{"appid": 99}]}})
    monkeypatch.setattr(get_ids, "create_session", lambda: FakeSession(response))
    assert get_ids.get_wishlist_ids("user") == [{"appid": 99}]


# ---------------------------------------------------------------------------
# get_playtime
# ---------------------------------------------------------------------------


def test_get_playtime(monkeypatch):
    response = FakeResponse(
        json_data={
            "response": {
                "games": [
                    {
                        "appid": 70,
                        "playtime_forever": 100,
                        "playtime_windows_forever": 60,
                        "playtime_mac_forever": 20,
                        "playtime_linux_forever": 20,
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(get_playtime, "create_session", lambda: FakeSession(response))
    assert get_playtime.get_playtime("key", "user") == [
        {
            "appid": 70,
            "playtime": 100,
            "playtime_windows": 60,
            "playtime_mac": 20,
            "playtime_linux": 20,
        }
    ]


def test_get_playtime_http_error_returns_empty(monkeypatch):
    response = FakeResponse(http_error=requests.exceptions.HTTPError("500"))
    monkeypatch.setattr(get_playtime, "create_session", lambda: FakeSession(response))
    assert get_playtime.get_playtime("key", "user") == []


def test_merge_recent_playtime_with_data():
    df = pd.DataFrame([{"appid": 70, "playtime": 100}])
    result = get_playtime.merge_recent_playtime(
        df, [{"appid": 70, "playtime_2weeks": 12}]
    )
    assert result["playtime_2weeks"].iloc[0] == 12


def test_merge_recent_playtime_without_recent_games():
    # Regression: an empty recent frame has no "appid" column to merge on.
    df = pd.DataFrame([{"appid": 70, "playtime": 100}])
    result = get_playtime.merge_recent_playtime(df, [])
    assert result["playtime_2weeks"].iloc[0] == 0
