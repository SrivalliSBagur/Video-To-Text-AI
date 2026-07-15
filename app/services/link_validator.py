import re
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "fb.watch",
]

MAX_DURATION_SECONDS = 1800  # 30 minutes max video length — guardrail

def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain

def is_allowed_url(url: str) -> bool:
    domain = extract_domain(url)
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_DOMAINS)

def detect_platform(url: str) -> str:
    domain = extract_domain(url)
    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif "instagram.com" in domain:
        return "instagram"
    elif "facebook.com" in domain or "fb.watch" in domain:
        return "facebook"
    return "unknown"

def extract_video_id(url: str) -> str | None:
    # YouTube
    yt_patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in yt_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Instagram and Facebook — return the URL path as ID (no standard short ID)
    parsed = urlparse(url)
    return parsed.path.strip("/").replace("/", "_") or None

def validate_link(url: str) -> dict:
    if not url or not url.startswith("http"):
        return {"valid": False, "error": "Invalid URL format. Must start with http/https."}

    if not is_allowed_url(url):
        return {"valid": False, "error": f"URL not allowed. Supported platforms: YouTube, Instagram, Facebook."}

    platform = detect_platform(url)
    video_id = extract_video_id(url)

    return {
        "valid": True,
        "platform": platform,
        "video_id": video_id,
        "url": url,
    }