"""Configuration management for Steam Stats.

This module centralizes configuration reading from config.ini files and environment variables.
"""

import os
import configparser
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SteamConfig:
    """Handles Steam API configuration from config.ini and environment variables.

    Configuration is read from either:
    1. Environment variables (highest priority)
    2. config.ini file (fallback)

    Environment variables:
    - STEAM_API_KEY: Steam API key
    - STEAM_USER_ID: Steam user ID (steamID64)
    - ITAD_API_KEY: IsThereAnyDeal API key
    """

    def __init__(self, config_path: str = "config.ini"):
        """Initialize configuration handler.

        Args:
            config_path: Path to config.ini file (default: "config.ini")
        """
        self.config_path = config_path
        self._config: Optional[configparser.ConfigParser] = None

    def _load_config(self) -> configparser.ConfigParser:
        """Lazy load config file.

        Returns:
            Loaded ConfigParser instance

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
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
        """Get Steam API key from environment or config file.

        Returns:
            Steam API key

        Raises:
            ValueError: If API key is not found in env or config
        """
        # Check environment variable first
        api_key = os.environ.get("STEAM_API_KEY")
        if api_key:
            logger.debug("Using Steam API key from STEAM_API_KEY environment variable")
            return api_key

        # Fall back to config file
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
        """Get Steam user ID from override, environment, or config file.

        Args:
            override: Explicit user ID to use (from command line args)

        Returns:
            Steam user ID (steamID64)

        Raises:
            ValueError: If user ID is not found
        """
        # Check override (from CLI args) first
        if override:
            logger.debug("Using Steam user ID from command line argument")
            return override

        # Check environment variable
        user_id = os.environ.get("STEAM_USER_ID")
        if user_id:
            logger.debug("Using Steam user ID from STEAM_USER_ID environment variable")
            return user_id

        # Fall back to config file
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
        """Get ITAD (IsThereAnyDeal) API key from environment or config file.

        Returns:
            ITAD API key

        Raises:
            ValueError: If ITAD API key is not found
        """
        # Check environment variable first
        api_key = os.environ.get("ITAD_API_KEY")
        if api_key:
            logger.debug("Using ITAD API key from ITAD_API_KEY environment variable")
            return api_key

        # Fall back to config file
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
