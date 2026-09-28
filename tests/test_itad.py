"""Tests for steam_stats.itad."""

import pytest

import steam_stats.itad as itad


class FakeJson:
    """Returns queued results from get_json and records requested URLs."""

    def __init__(self, *results):
        self._results = list(results)
        self.urls = []

    def __call__(self, session, url, timeout=None):
        self.urls.append(url)
        if not self._results:
            return None
        if len(self._results) == 1:
            return self._results[0]
        return self._results.pop(0)


@pytest.fixture
def patch_get_json(monkeypatch):
    def _apply(*results):
        fake = FakeJson(*results)
        monkeypatch.setattr(itad, "get_json", fake)
        return fake

    return _apply


def test_get_itad_plain_success(patch_get_json):
    patch_get_json({"data": {"plain": "abc123"}})
    assert itad.get_itad_plain(None, "key", "70") == "abc123"


def test_get_itad_plain_missing_data(patch_get_json):
    patch_get_json({"data": {}})
    assert itad.get_itad_plain(None, "key", "70") is None


def test_get_itad_plain_no_result(patch_get_json):
    patch_get_json(None)
    assert itad.get_itad_plain(None, "key", "70") is None


def test_get_itad_historical_low(patch_get_json):
    patch_get_json(
        {
            "data": {"abc123": {"price": 4.99, "shop": {"name": "Steam"}}},
            ".meta": {"currency": "EUR"},
        }
    )
    result = itad.get_itad_historical_low(None, "key", "abc123")
    assert result == {
        "historical_low_price": 4.99,
        "historical_low_currency": "EUR",
        "historical_low_shop": "Steam",
    }


def test_get_itad_historical_low_missing_game(patch_get_json):
    patch_get_json({"data": {}, ".meta": {"currency": "EUR"}})
    assert itad.get_itad_historical_low(None, "key", "abc123") is None


def test_get_itad_current_price_prefers_matching_url(patch_get_json):
    patch_get_json(
        {
            "data": {
                "abc123": {
                    "list": [
                        {
                            "price_new": 9.99,
                            "url": "https://other/app/999",
                            "shop": {"name": "Other"},
                        },
                        {
                            "price_new": 4.99,
                            "url": "https://steam/app/70",
                            "shop": {"name": "Steam"},
                        },
                    ]
                }
            },
            ".meta": {"currency": "EUR"},
        }
    )
    result = itad.get_itad_current_price(None, "key", "70", "abc123")
    assert result == {
        "current_price_price": 4.99,
        "current_price_currency": "EUR",
        "current_price_shop": "Steam",
    }


def test_get_itad_current_price_falls_back_to_first(patch_get_json):
    patch_get_json(
        {
            "data": {
                "abc123": {
                    "list": [
                        {
                            "price_new": 9.99,
                            "url": "https://other/app/999",
                            "shop": {"name": "Other"},
                        }
                    ]
                }
            },
            ".meta": {"currency": "EUR"},
        }
    )
    result = itad.get_itad_current_price(None, "key", "70", "abc123")
    assert result["current_price_price"] == 9.99


def test_get_itad_current_price_empty_list(patch_get_json):
    patch_get_json({"data": {"abc123": {"list": []}}, ".meta": {"currency": "EUR"}})
    assert itad.get_itad_current_price(None, "key", "70", "abc123") is None


def test_get_itad_data_combines_both(patch_get_json):
    patch_get_json(
        {"data": {"plain": "abc123"}},
        {
            "data": {"abc123": {"price": 4.99, "shop": {"name": "Steam"}}},
            ".meta": {"currency": "EUR"},
        },
        {
            "data": {
                "abc123": {
                    "list": [
                        {
                            "price_new": 2.5,
                            "url": "steam/app/70",
                            "shop": {"name": "Steam"},
                        }
                    ]
                }
            },
            ".meta": {"currency": "EUR"},
        },
    )
    result = itad.get_itad_data(None, "key", "70")
    assert result["plain"] == "abc123"
    assert result["historical_low_price"] == 4.99
    assert result["current_price_price"] == 2.5


def test_get_itad_data_no_plain_returns_none(patch_get_json):
    patch_get_json({"data": {}})
    assert itad.get_itad_data(None, "key", "70") is None


def test_get_itad_data_no_prices_returns_none(patch_get_json):
    patch_get_json({"data": {"plain": "abc123"}}, None, None)
    assert itad.get_itad_data(None, "key", "70") is None
