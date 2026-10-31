"""
Module: core.config
Author: Shlok Shah (@ShlokShah2007)
Purpose: System Configuration & Storage Node Registry
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables from .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Default Shared API Key for Storage Node Authentication
DEFAULT_API_KEY = "chunk_sec_key_9f82ab71c94e01d8"
STORAGE_API_KEY = os.getenv("STORAGE_API_KEY", DEFAULT_API_KEY)

# Storage Node Endpoints
DEFAULT_NODES = [
    os.getenv("NODE_1_URL", "http://127.0.0.1:8001"),
    os.getenv("NODE_2_URL", "http://127.0.0.1:8002"),
    os.getenv("NODE_3_URL", "http://127.0.0.1:8003"),
]

# Chunk settings
DEFAULT_CHUNK_SIZE_BYTES = int(os.getenv("DEFAULT_CHUNK_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB default
