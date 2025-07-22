import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def get_api_key():
    """Load Polygon API key from environment variable."""
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError("Polygon API key not found in environment variable POLYGON_API_KEY")
    return api_key

def log_info(msg):
    """Simple logger."""
    print(f"[INFO] {msg}")

def handle_rate_limit():
    """Sleep to respect Polygon free tier rate limit (5 calls/minute)."""
    time.sleep(13)  # 60 seconds / 5 calls = 12s, add buffer this will prevent api time outs