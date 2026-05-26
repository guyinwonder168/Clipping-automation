"""ElevenLabs text-to-speech service."""

import os
from pathlib import Path

import httpx


class ElevenLabsService:
    """Text-to-speech generation via ElevenLabs API."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY")

    def generate_voice(
        self, text: str, voice_id: str, output_path: str
    ) -> str:
        """Generate speech audio from text and write to a file.

        Returns:
            The output file path.
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with httpx.Client(base_url=self.BASE_URL, timeout=120) as client:
            resp = client.post(
                f"/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.7},
                },
            )
            resp.raise_for_status()
            path.write_bytes(resp.content)

        return str(path)
