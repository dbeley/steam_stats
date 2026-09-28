"""Shared test fixtures and path setup.

The ``steam_stats`` package and the standalone ``scripts/`` modules are
imported directly from the source tree (the package is not installed during
tests), so both locations are added to ``sys.path``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

for path in (REPO_ROOT, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
