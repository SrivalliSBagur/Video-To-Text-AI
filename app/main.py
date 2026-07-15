from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

from app.services.link_validator import validate_link
from app.services.audio_extractor import extract_audio
from app.services.transcriber import transcribe_audio, is_transcript_useful
from app.services.classifier import classify_content
from app.services.summarizer import summarize
from app.services.guardrails import (
    check_rate_limit,
    sanitize_url,
    get_cached_result,
    save_to_cache,
    log_request
)

app = FastAPI(
    title="Video to Text AI",
    description="Converts any YouTube/Instagram/Facebook video into structured content",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "ok", "message": "Video to Text AI is running"}


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "message": "All systems operational"}


@app.post("/process")
async def process_video(request: Request, body: VideoRequest):
    start_time = time.time()

    # Get client IP for rate limiting
    client_ip = request.client.host

    # Guardrail 1 — Rate limit
    rate_check = check_rate_limit(client_ip)
    if not rate_check["allowed"]:
        raise HTTPException(status_code=429, detail=rate_check["error"])

    # Guardrail 2 — Sanitize URL
    clean_url = sanitize_url(body.url)

    # Guardrail 3 — Check cache first
    cached = get_cached_result(clean_url)
    if cached:
        log_request(
            client_ip=client_ip,
            url=clean_url,
            platform=cached.get("platform", "unknown"),
            content_type=cached.get("content_type", "unknown"),
            success=True,
            duration=0,
            from_cache=True
        )
        return cached

    # Guardrail 4 — Validate link
    validation = validate_link(clean_url)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])

    platform = validation["platform"]
    video_id = validation["video_id"]

    # Step 1 — Extract audio
    audio_result = extract_audio(clean_url, video_id)
    if not audio_result["success"]:
        raise HTTPException(status_code=422, detail=f"Audio extraction failed: {audio_result['error']}")

    # Step 2 — Transcribe
    transcript_result = transcribe_audio(audio_result["audio_path"])
    if not transcript_result["success"]:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {transcript_result['error']}")

    transcript = transcript_result["transcript"]

    # Guardrail 5 — Check transcript quality
    if not is_transcript_useful(transcript):
        raise HTTPException(
            status_code=422,
            detail="This video appears to have no spoken content or insufficient audio. "
                   "Silent videos, music-only videos, or videos in unsupported languages "
                   "cannot be processed. Please try a video with clear speech."
        )

    # Step 3 — Classify
    classification = classify_content(transcript)
    content_type = classification.get("content_type", "general")

    # Step 4 — Summarize
    summary = summarize(transcript, content_type)
    if not summary["success"]:
        raise HTTPException(status_code=422, detail=f"Summarization failed: {summary['error']}")

    elapsed = round(time.time() - start_time, 2)

    result = {
        "success": True,
        "platform": platform,
        "video_id": video_id,
        "title": audio_result.get("title", "Unknown"),
        "duration": audio_result.get("duration", 0),
        "language": transcript_result.get("language", "unknown"),
        "content_type": content_type,
        "classification_confidence": classification.get("confidence", "low"),
        "classification_reason": classification.get("reason", ""),
        "transcript": transcript,
        "output": summary["output"],
        "processing_time_seconds": elapsed,
        "from_cache": False,
    }

    # Save to cache + log
    save_to_cache(clean_url, result)
    log_request(
        client_ip=client_ip,
        url=clean_url,
        platform=platform,
        content_type=content_type,
        success=True,
        duration=elapsed,
        from_cache=False
    )

    return result