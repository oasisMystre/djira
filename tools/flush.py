"""
Script written by Oguntunde Caleb Fiyinfoluwa <oasis.mystre@gmail.com>

I hate __pycache__ files and unnecessary build files luking around by project?
Use this script to recursivly remove these files from your workspace 😁😁

I love recursion, It's mutual
>>> Only me and God know how this is written, Now only God knows >> I love this line from @fireship.io
"""

import os
import shutil
from pathlib import Path

from typing import Callable, List

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def flush(dir: Path, search: str, worker: Callable[[Path], None]):
    """
    Remove certain folder or files recursively
    """

    for folder in os.listdir(dir):
        path = dir / folder

        if search in str(path):
            worker(path)
        elif os.path.isdir(path):
            flush(path, search, worker)


def depthDelete(dir: Path, excludes: List[str]):
    """
    Depth delete files with excludes,
    This is  used along side flush as plugin
    """
    for file in os.listdir(dir):
        if file not in excludes:
            os.remove(dir / file)


flush(BASE_DIR, "__pycache__", lambda dir: shutil.rmtree(dir))

"""
For django based projects use this
"""

flush(BASE_DIR, "migrations", lambda dir: depthDelete(dir, ["__init__.py"]))

dbPath = BASE_DIR / "example" / "db.sqlite3"

if os.path.exists(dbPath):
    os.remove(dbPath)
