"""
Speech-to-Text service using Sarvam AI (Saaras v3).
Optimized for Indian languages: English, Hindi, Telugu.
Replaces local Faster-Whisper with Sarvam's cloud API.
"""

import os
import tempfile
import requests
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()


class WhisperService:
    """Service for transcribing audio using Sarvam AI Saaras STT API."""

    _instance = None

    SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"

    @classmethod
    def get_instance(cls) -> "WhisperService":
        """Singleton pattern for reuse."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize with Sarvam API key."""
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            print("WARNING: SARVAM_API_KEY not set. STT will not work.")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> Tuple[str, float]:
        """
        Transcribe audio bytes to text using Sarvam AI.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename for extension detection

        Returns:
            Tuple of (transcript text, duration in seconds)
        """
        # Determine file extension
        ext = os.path.splitext(filename)[1].lower() if filename else ".webm"
        if not ext:
            ext = ".webm"

        # Determine content type
        mime_map = {
            ".webm": "audio/webm",
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
            ".opus": "audio/opus",
        }
        content_type = mime_map.get(ext, "audio/webm")
        safe_filename = f"recording{ext}"

        try:
            # Call Sarvam AI STT API directly from bytes
            files = {
                "file": (safe_filename, audio_bytes, content_type),
            }
            data = {
                "model": "saaras:v3",
                "mode": "translate",
                "with_timestamps": "false",
            }
            headers = {
                "api-subscription-key": self.api_key,
            }

            response = requests.post(
                self.SARVAM_API_URL,
                files=files,
                data=data,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"Sarvam API error ({response.status_code}): {error_detail}")
                raise Exception(f"Sarvam STT failed: {response.status_code}")

            result = response.json()

            # Extract transcript from response
            transcript = result.get("transcript", "")

            # Sarvam may return language_code
            language = result.get("language_code", "unknown")

            # Duration estimate
            duration = result.get("duration", 0.0)

            return transcript.strip(), duration

        except requests.exceptions.Timeout:
            raise Exception("Sarvam API timeout — recording may be too long (max 30s)")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not reach Sarvam API — check internet connection")
