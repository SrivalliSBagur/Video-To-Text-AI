import yt_dlp
import os

AUDIO_OUTPUT_DIR = "outputs/audio"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

def extract_audio(url: str, video_id: str) -> dict:
    """
    Downloads audio from a YouTube/Instagram/Facebook URL.
    Returns the path to the downloaded .mp3 file and video metadata.
    """
    output_path = os.path.join(AUDIO_OUTPUT_DIR, f"{video_id}")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            duration = info.get("duration", 0)
            title = info.get("title", "Unknown Title")

            # Guardrail — reject videos longer than 10 minutes
            if duration > 600:
                return {
                    "success": False,
                    "error": f"Video is too long ({duration // 60} mins). Max allowed is 10 minutes."
                }

            return {
                "success": True,
                "audio_path": output_path + ".mp3",
                "duration": duration,
                "title": title,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}