from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_VIDEO_DURATION = 600  # 10 minutes
ALLOWED_PLATFORMS = ["youtube", "instagram", "facebook"]