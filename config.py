"""
config.py — SINGLE source of truth for all credentials and settings.

Reads from .env file using python-dotenv.
Every script imports from here. No credentials anywhere else.
"""

import os
from dotenv import load_dotenv

# Load .env file if it exists (won't fail if missing — Phase 1 doesn't need secrets)
load_dotenv()

# MongoDB Atlas (Phase 2+)
MONGO_URI = os.getenv("MONGO_URI", "")

# Experimental sandbox (Phase 3R+) — points at the schooldaylight_experiment
# database on the same Atlas cluster. Used by experimental scripts so production
# and experimental code paths can never accidentally cross. Every experimental
# script must verify its database name contains "experiment" before any write.
MONGO_URI_EXPERIMENT = os.getenv("MONGO_URI_EXPERIMENT", "")

# Database names — single source of truth. Experimental scripts use the
# *_EXPERIMENT name; production scripts use the unsuffixed name.
DB_NAME = "schooldaylight"
DB_NAME_EXPERIMENT = "schooldaylight_experiment"

# Anthropic API (Phase 4+)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Project paths — so scripts don't hardcode paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(PROJECT_ROOT, "WA-raw")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
PHASES_DIR = os.path.join(PROJECT_ROOT, "phases")
