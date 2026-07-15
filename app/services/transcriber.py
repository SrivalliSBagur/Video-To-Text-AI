import whisper
import os

# Load once at module level so it doesn't reload on every call
# "base" is fast and good enough — can upgrade to "small" or "medium" later
model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> dict:
    """
    Takes a path to an mp3 file and returns the full transcript text.
    """
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    try:
        result = model.transcribe(audio_path, fp16=False)
        return {
            "success": True,
            "transcript": result["text"].strip(),
            "language": result.get("language", "unknown"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def is_transcript_useful(transcript: str) -> bool:
    """
    Returns False if the transcript is too short or looks like
    it came from a silent/music-only video.
    """
    words = transcript.strip().split()

    # Too short to be useful
    if len(words) < 30:
        return False

    # Looks like noise — repeated characters, no real sentences
    unique_words = set(w.lower() for w in words)
    if len(unique_words) < 10:
        return False

    return True