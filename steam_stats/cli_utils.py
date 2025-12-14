"""Shared CLI utilities for steam_stats and scripts.

This module provides common command-line argument parsing and setup functions
to reduce code duplication across the main package and helper scripts.
"""

import argparse
import logging
from typing import Optional


def add_debug_argument(parser: argparse.ArgumentParser) -> None:
    """Add standard --debug flag to argument parser.

    Args:
        parser: ArgumentParser instance to add the argument to
    """
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )


def add_user_id_argument(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
    """Add standard -u/--user_id flag to argument parser.

    Args:
        parser: ArgumentParser instance to add the argument to
        required: Whether the user_id argument is required
    """
    parser.add_argument(
        "-u",
        "--user_id",
        help=(
            "Steam user ID (steamID64) to extract data from. "
            "Default: value from config.ini or STEAM_USER_ID environment variable"
        ),
        type=str,
        required=required,
    )


def add_filename_argument(
    parser: argparse.ArgumentParser,
    help_text: str,
    required: bool = False,
    dest: str = "filename",
) -> None:
    """Add standard -f/--filename flag to argument parser.

    Args:
        parser: ArgumentParser instance to add the argument to
        help_text: Help text describing what file is expected
        required: Whether the filename argument is required
        dest: Destination variable name (default: "filename")
    """
    # Support both --filename and --file for backwards compatibility
    if dest == "filename":
        parser.add_argument(
            "-f",
            "--filename",
            help=help_text,
            type=str,
            required=required,
        )
    else:
        parser.add_argument(
            "-f",
            "--file",
            dest=dest,
            help=help_text,
            type=str,
            required=required,
        )


def setup_logging(
    level: int = logging.INFO, format_string: Optional[str] = None
) -> None:
    """Configure logging with consistent format.

    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        format_string: Optional custom format string. If None, uses default.
    """
    if format_string is None:
        format_string = "%(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=format_string,
    )


def create_base_parser(description: str) -> argparse.ArgumentParser:
    """Create a base argument parser with common arguments.

    This is useful for scripts that share common patterns.

    Args:
        description: Description of the script/tool

    Returns:
        Configured ArgumentParser with debug flag
    """
    parser = argparse.ArgumentParser(description=description)
    add_debug_argument(parser)
    return parser
