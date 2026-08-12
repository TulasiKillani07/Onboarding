"""
Sarvam AI Speech-to-Text service (Saaras v3).

Responsibility: Accept audio bytes, return transcript string.
This module knows nothing about NER or entity extraction.

Uses shared httpx.AsyncClient for connection pooling and retry.
"""

import os
from typing import Tuple
from dotenv import load_dotenv
from app.http_client import HttpClient
from app.utils.logger import get_dobo_logger

load_dotenv()

logger = get_dobo_logger(__name__)


class SarvamService:
    """Transcribes audio using Sarvam AI Saaras v3 STT API."""

    _instance = None
    SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"

    @classmethod
    def get_instance(cls) -> "SarvamService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not set. STT will not work.")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> Tuple[str, float]:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio file bytes
            filename:    Original filename (for MIME type detection)

        Returns:
            (transcript: str, duration: float)
        """
        ext = os.path.splitext(filename)[1].lower() if filename else ".webm"
        if not ext:
            ext = ".webm"

        mime_map = {
            ".webm": "audio/webm", ".wav": "audio/wav",
            ".mp3":  "audio/mpeg", ".ogg": "audio/ogg",
            ".m4a":  "audio/mp4",  ".aac": "audio/aac",
            ".flac": "audio/flac", ".opus": "audio/opus",
        }
        content_type  = mime_map.get(ext, "audio/webm")
        safe_filename = f"recording{ext}"

        logger.info(f"STT request | size={len(audio_bytes)} ext={ext}")

        import httpx

        try:
            response = await HttpClient.request_with_retry(
                "POST",
                self.SARVAM_API_URL,
                files={"file": (safe_filename, audio_bytes, content_type)},
                data={"model": "saaras:v3", "mode": "translate", "with_timestamps": "false"},
                headers={"api-subscription-key": self.api_key},
            )

            if response.status_code != 200:
                logger.error(f"Sarvam STT failed | status={response.status_code}")
                raise Exception(f"Sarvam STT failed: {response.status_code} - {response.text}")

            result = response.json()
            transcript = result.get("transcript", "").strip()
            duration = result.get("duration", 0.0)

            logger.info(f"STT success | duration={duration:.1f}s transcript_len={len(transcript)}")
            # Debug only: never log raw transcript at INFO (contains PII)
            logger.debug(f"STT transcript (truncated): {transcript[:50]}...")

            return transcript, duration

        except httpx.TimeoutException:
            logger.error("Sarvam API timeout")
            raise Exception("Sarvam API timeout - recording may be too long (max 30s)")
        except httpx.ConnectError:
            logger.error("Sarvam API unreachable")
            raise Exception("Could not reach Sarvam API - check internet connection")
