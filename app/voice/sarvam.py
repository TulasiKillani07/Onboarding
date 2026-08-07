"""
Sarvam AI Speech-to-Text service (Saaras v3).

Responsibility: Accept audio bytes, return transcript string.
This module knows nothing about NER or entity extraction.
"""

import os
import requests
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()


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
            print("WARNING: SARVAM_API_KEY not set. STT will not work.")

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

        try:
            response = requests.post(
                self.SARVAM_API_URL,
                files={"file": (safe_filename, audio_bytes, content_type)},
                data={"model": "saaras:v3", "mode": "translate", "with_timestamps": "false"},
                headers={"api-subscription-key": self.api_key},
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"Sarvam STT failed: {response.status_code} — {response.text}")

            result = response.json()
            return result.get("transcript", "").strip(), result.get("duration", 0.0)

        except requests.exceptions.Timeout:
            raise Exception("Sarvam API timeout — recording may be too long (max 30s)")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not reach Sarvam API — check internet connection")
