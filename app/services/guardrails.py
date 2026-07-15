import time
import hashlib
import json
import os
from datetime import datetime
from collections import defaultdict

# ─── Rate Limiter ──────────────────────────────────────────
# Stores request timestamps per IP
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_MAX = 5        # max requests
RATE_LIMIT_WINDOW = 3600  # per hour (in seconds)

def check_rate_limit(client_ip: str) -> dict:
    """
    Allows max 5 requests per hour per IP.
    Returns allowed: True/False and remaining count.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Remove timestamps outside the window
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]

    count = len(_rate_limit_store[client_ip])

    if count >= RATE_LIMIT_MAX:
        wait_seconds = int(_rate_limit_store[client_ip][0] + RATE_LIMIT_WINDOW - now)
        wait_minutes = wait_seconds // 60
        return {
            "allowed": False,
            "error": f"Rate limit exceeded. You've used {count}/{RATE_LIMIT_MAX} requests this hour. "
                     f"Try again in {wait_minutes} minutes."
        }

    _rate_limit_store[client_ip].append(now)
    return {
        "allowed": True,
        "remaining": RATE_LIMIT_MAX - count - 1
    }


# ─── URL Sanitizer ─────────────────────────────────────────
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

TRACKING_PARAMS = [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "feature", "pp", "si", "igshid"
]

def sanitize_url(url: str) -> str:
    """
    Strips tracking parameters from URLs.
    e.g. youtube.com/watch?v=abc&utm_source=twitter → youtube.com/watch?v=abc
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove known tracking params
    cleaned_params = {
        k: v for k, v in params.items()
        if k.lower() not in TRACKING_PARAMS
    }

    cleaned_query = urlencode(cleaned_params, doseq=True)
    cleaned_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        cleaned_query,
        parsed.fragment
    ))

    return cleaned_url


# ─── Cache (Duplicate Detection) ───────────────────────────
CACHE_DIR = "outputs/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def get_cached_result(url: str) -> dict | None:
    """
    Returns cached result if this URL was processed before.
    """
    key = _get_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                cached["from_cache"] = True
                return cached
        except:
            return None
    return None

def save_to_cache(url: str, result: dict):
    """
    Saves a result to cache so repeat requests are instant.
    """
    key = _get_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass  # cache failure is non-critical


# ─── Request Logger ────────────────────────────────────────
LOG_DIR = "outputs/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "requests.jsonl")

def log_request(client_ip: str, url: str, platform: str,
                content_type: str, success: bool,
                duration: float, from_cache: bool = False):
    """
    Appends one log entry per request to a JSONL file.
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "client_ip": client_ip,
        "url": url,
        "platform": platform,
        "content_type": content_type,
        "success": success,
        "processing_time_seconds": duration,
        "from_cache": from_cache,
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass  # logging failure is non-critical