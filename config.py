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

# Anthropic API (Phase 4+)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Project paths — so scripts don't hardcode paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(PROJECT_ROOT, "WA-raw")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
PHASES_DIR = os.path.join(PROJECT_ROOT, "phases")
