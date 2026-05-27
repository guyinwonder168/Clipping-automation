"""Voice Producer Agent — text-to-speech generation via ElevenLabs."""

import logging
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.services.elevenlabs import ElevenLabsService

logger = logging.getLogger(__name__)


class VoiceProducerAgent(BaseAgent):
    """Converts script scenes to audio files using ElevenLabs TTS."""

    @property
    def agent_name(self) -> str:
        return "voice_producer"

    def execute(
        self,
        job_id: int,
        script: list[dict] | None = None,
        output_dir: str = "",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        **kwargs: Any,
    ) -> dict[str, Any]:
        scenes = script or []
        audio_files: list[str] = []

        if not scenes:
            logger.info("Voice: no scenes to process")
            return {"status": "completed", "audio_files": audio_files}

        logger.info("Voice: generating TTS for %d scenes", len(scenes))
        try:
            service = ElevenLabsService()
            for i, scene in enumerate(scenes):
                text = scene.get("text", "")
                output_path = f"{output_dir}/job_{job_id}/scene_{i}.mp3"
                path = service.generate_voice(text, voice_id, output_path)
                audio_files.append(path)

            logger.info("Voice: completed %d audio files", len(audio_files))
            return {"status": "completed", "audio_files": audio_files}
        except Exception as e:
            logger.error("Voice: TTS generation failed — %s", e)
            return {"status": "failed", "error": str(e), "audio_files": audio_files}
