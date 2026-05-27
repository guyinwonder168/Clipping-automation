"""Voice Producer Agent — text-to-speech generation.

Supports both ElevenLabs and Fish Audio providers. Dispatching is
automatic based on which API key is configured (fish_audio preferred
when both are set).
"""

import logging
import os
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.services.elevenlabs import ElevenLabsService
from clipper_agency.services.fish_audio import FishAudioService

logger = logging.getLogger(__name__)

# Default voice IDs per provider
# Fish Audio: use any public model ID from api.fish.audio/model
# ElevenLabs: "Rachel" voice
_voice_ids = {
    "elevenlabs": "21m00Tcm4TlvDq8ikWAM",
    "fish_audio": "",
}


class VoiceProducerAgent(BaseAgent):
    """Converts script scenes to audio files using configured TTS provider."""

    @property
    def agent_name(self) -> str:
        return "voice_producer"

    def execute(
        self,
        job_id: int,
        script: list[dict] | None = None,
        output_dir: str = "",
        voice_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        scenes = script or []
        audio_files: list[str] = []

        if not scenes:
            logger.info("Voice: no scenes to process")
            return {"status": "completed", "audio_files": audio_files}

        provider = self._detect_provider()
        resolved_voice_id = voice_id or _voice_ids.get(provider, "")

        logger.info(
            "Voice: generating TTS for %d scenes (provider=%s)",
            len(scenes), provider,
        )
        try:
            service = self._create_service(provider)
            for i, scene in enumerate(scenes):
                text = scene.get("text", "")
                output_path = f"{output_dir}/job_{job_id}/scene_{i}.mp3"
                path = service.generate_voice(text, resolved_voice_id, output_path)
                audio_files.append(path)

            logger.info("Voice: completed %d audio files", len(audio_files))
            return {"status": "completed", "audio_files": audio_files}
        except Exception as e:
            logger.exception("Voice: TTS generation failed (provider=%s)", provider)
            return {"status": "failed", "error": str(e), "audio_files": audio_files}

    def _detect_provider(self) -> str:
        """Return which TTS provider to use based on configured API keys.

        Fish Audio preferred when both keys are set (cheaper, not blocked).
        """
        if os.getenv("FISH_AUDIO_API_KEY") or os.getenv("FISHAUDIO_KEY"):
            return "fish_audio"
        if os.getenv("ELEVENLABS_API_KEY"):
            return "elevenlabs"
        raise ValueError("No TTS API key configured (FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY)")

    def _create_service(self, provider: str):
        """Create the TTS service instance for the given provider."""
        if provider == "fish_audio":
            return FishAudioService()
        if provider == "elevenlabs":
            return ElevenLabsService()
        raise ValueError(f"Unknown TTS provider: {provider}")
