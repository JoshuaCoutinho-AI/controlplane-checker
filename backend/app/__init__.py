"""
Loads .env (from the project root) before any submodule reads its
config from the environment. This must happen here, in the package
__init__, rather than in main.py — Python runs a package's __init__.py
before any of its submodules, so this guarantees db.py and
llm_provider.py (which read os.getenv(...) at import time, not inside
a function) see variables from .env instead of only picking up
whatever was already exported in the shell.

find_dotenv() walks upward from this file's directory looking for a
.env, so this works regardless of which directory `uvicorn` is
launched from (e.g. running it from backend/ still finds the .env
that sits at the project root, one level up).
"""

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
