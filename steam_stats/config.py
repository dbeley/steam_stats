import os
import configparser
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SteamConfig:
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self._config: Optional[configparser.ConfigParser] = None

    def _load_config(self) -> configparser.ConfigParser:
        if self._config is None:
            self._config = configparser.ConfigParser()
            if not Path(self.config_path).exists():
                raise FileNotFoundError(
                    f"Config file not found: {self.config_path}. "
                    "Copy config_sample.ini to config.ini and fill in your API keys."
                )
            self._config.read(self.config_path)
        return self._config

    def get_api_key(self) -> str:
        api_key = os.environ.get("STEAM_API_KEY")
        if api_key:
            logger.debug("Using Steam API key from STEAM_API_KEY environment variable")
            return api_key

        try:
            config = self._load_config()
            api_key = config["steam"]["api_key"]
            logger.debug("Using Steam API key from config.ini")
            return api_key
        except KeyError:
            raise ValueError(
                "No Steam API key found. Set STEAM_API_KEY environment variable "
                "or add api_key in [steam] section of config.ini"
            )

    def get_user_id(self, override: Optional[str] = None) -> str:
        if override:
            logger.debug("Using Steam user ID from command line argument")
            return override

        user_id = os.environ.get("STEAM_USER_ID")
        if user_id:
            logger.debug("Using Steam user ID from STEAM_USER_ID environment variable")
            return user_id

        try:
            config = self._load_config()
            user_id = config["steam"]["user_id"]
            logger.debug("Using Steam user ID from config.ini")
            return user_id
        except KeyError:
            raise ValueError(
                "No Steam user ID found. Use -u/--user_id flag, set STEAM_USER_ID "
                "environment variable, or add user_id in [steam] section of config.ini"
            )

    def get_itad_api_key(self) -> str:
        api_key = os.environ.get("ITAD_API_KEY")
        if api_key:
            logger.debug("Using ITAD API key from ITAD_API_KEY environment variable")
            return api_key

        try:
            config = self._load_config()
            api_key = config["itad"]["api_key"]
            logger.debug("Using ITAD API key from config.ini")
            return api_key
        except KeyError:
            raise ValueError(
                "No ITAD API key found. Set ITAD_API_KEY environment variable "
                "or add api_key in [itad] section of config.ini"
            )
