"""Orchestrator Engine — coordinates the full gated agent pipeline."""

import logging
from typing import Any

from clipper_agency.agents.composer import ComposerAgent
from clipper_agency.agents.researcher import ResearcherAgent
from clipper_agency.agents.reviewer import ReviewerAgent
from clipper_agency.agents.safety import SafetyAgent
from clipper_agency.agents.scriptwriter import ScriptwriterAgent
from clipper_agency.agents.visual_director import VisualDirectorAgent
from clipper_agency.agents.voice_producer import VoiceProducerAgent
from clipper_agency.config.loader import load_settings
from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import (
    create_agent_state,
    create_job,
    update_job_status,
)
from clipper_agency.db.schema import initialize_schema
from clipper_agency.orchestrator.gates import (
    GateCostEstimate,
    GateInputPreflight,
    GatePostResearchRisk,
    GateResearchCache,
    GateSourceQuality,
    GateCreativeMemory,
    GateScriptValidation,
    GateAudioValidation,
    GateAssetValidation,
    GateVideoValidation,
)
from clipper_agency.output.packager import OutputPackager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the full gated agent pipeline: Topic → Output Package."""

    def __init__(self, db_path: str = "data/clipper.db") -> None:
        self.db_path = db_path
        conn = get_connection(db_path)
        initialize_schema(conn)

    def run_pipeline(
        self,
        topic: str,
        niche: str = "indonesian_artists",
        output_dir: str = "outputs",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the full topic-to-output pipeline.

        Gate sequence: G1→G2→Safety→G3→Researcher→G4→G5→G6→
                       Scriptwriter→G7→Voice→G8→Visual→G9→
                       Composer→G10→Reviewer→Package
        """
        conn = get_connection(self.db_path)
        settings = load_settings()
        assets_cache = str(kwargs.get("assets_cache") or settings.assets_cache)
        logger.info("Pipeline START: niche='%s'", niche)

        # G1: Input Preflight
        g1 = GateInputPreflight()
        g1_result = g1.evaluate(topic=topic, niche_config={"name": niche})
        if not g1_result.passed:
            logger.error("G1 Preflight FAILED: %s", g1_result.message)
            update_job_status(conn, 0, "FAILED", g1_result.message)
            return {"status": "failed", "failed_at": "preflight",
                    "reason": g1_result.message, "job_id": 0}

        # Create job in DB
        job_id = create_job(conn, topic=topic, niche=niche)
        logger.info("Job #%d created", job_id)
        agent_names = [
            "safety", "researcher", "scriptwriter",
            "voice_producer", "visual_director", "composer", "reviewer",
        ]
        for name in agent_names:
            create_agent_state(conn, job_id, name)

        try:
            # G2: Cost Estimate
            g2 = GateCostEstimate()
            cost_result = g2.evaluate()

            # Safety Agent (via delegating method for testability)
            logger.info("G2: running Safety agent")
            safety_result = self._run_safety(
                job_id=job_id,
                topic=topic,
                assets_cache=assets_cache,
            )
            if safety_result.get("status") == "hard_fail":
                logger.error("Safety FAILED: %s", safety_result.get("reason"))
                update_job_status(conn, job_id, "FAILED", safety_result["reason"])
                return {
                    "status": "failed",
                    "failed_at": "safety",
                    "reason": safety_result["reason"],
                    "job_id": job_id,
                }

            safety_rules = [
                "no_defamation",
                "mark_rumors_as_unconfirmed",
            ]

            # G3: Research Cache Check
            g3 = GateResearchCache()
            g3.evaluate()

            # Researcher Agent
            logger.info("G3: running Researcher agent")
            research_output = self._run_researcher(
                job_id=job_id, topic=topic, safety_rules=safety_rules,
                output_dir=output_dir,
                assets_cache=assets_cache,
            )

            # G4: Post-Research Risk
            g4 = GatePostResearchRisk()
            g4_result = g4.evaluate(
                risk_flags=research_output.get("risk_flags", []),
            )
            if not g4_result.passed and g4_result.severity == "hard_fail":
                update_job_status(conn, job_id, "FAILED", g4_result.message)
                return {
                    "status": "failed",
                    "failed_at": "post_research_risk",
                    "reason": g4_result.message,
                    "job_id": job_id,
                }

            # G5: Source Quality
            g5 = GateSourceQuality()
            g5.evaluate(
                video_sources=research_output.get("sources", []),
            )

            # G6: Creative Memory
            g6 = GateCreativeMemory()
            g6.evaluate()

            # Scriptwriter Agent
            logger.info("G6: running Scriptwriter agent")
            script_output = self._run_scriptwriter(
                job_id=job_id,
                topic=topic,
                research_brief=research_output.get("research_brief", ""),
                safety_rules=safety_rules,
                assets_cache=assets_cache,
            )

            # G7: Script Validation (extract text from scene list)
            g7 = GateScriptValidation()
            script_scenes = script_output.get("script", [])
            script_text = " ".join(
                s.get("text", "") for s in script_scenes
            ) if isinstance(script_scenes, list) else str(script_scenes)
            g7.evaluate(
                script=script_text,
                caption=script_output.get("caption", ""),
            )

            # Voice Producer Agent
            logger.info("G7: running Voice Producer agent")
            voice_output = self._run_voice_producer(
                job_id=job_id,
                script=script_output.get("script", []),
                output_dir=output_dir,
                assets_cache=assets_cache,
            )

            # G8: Audio Validation
            g8 = GateAudioValidation()
            audio_list = voice_output.get("audio_files") or []
            first_audio = audio_list[0] if audio_list else None
            g8.evaluate(audio_path=first_audio)

            # Visual Director Agent
            logger.info("G8: running Visual Director agent")
            sources_data = research_output.get("sources", {})
            if isinstance(sources_data, dict):
                research_sources = sources_data.get("sources", [])
            elif isinstance(sources_data, list):
                research_sources = sources_data
            else:
                research_sources = []
            source_urls = [s["url"] for s in research_sources
                           if isinstance(s, dict) and s.get("url")]
            visual_output = self._run_visual_director(
                job_id=job_id,
                script=script_output.get("script", []),
                topic=topic,
                source_urls=source_urls,
                output_dir=output_dir,
            )

            # G9: Asset Validation
            g9 = GateAssetValidation()
            asset_paths = [a.get("path", "") for a in visual_output.get("assets", [])]
            g9.evaluate(asset_paths=asset_paths)

            # Composer Agent
            logger.info("G9: running Composer agent")
            compose_output = self._run_composer(
                job_id=job_id,
                assets=visual_output.get("assets", []),
                audio_files=voice_output.get("audio_files", []),
                output_dir=output_dir,
            )

            # Check composer failure
            if compose_output.get("status") == "failed":
                logger.error("Composer FAILED: %s", compose_output.get("error"))
                update_job_status(conn, job_id, "FAILED",
                                  compose_output.get("error", "Composer failed"))
                return {
                    "status": "failed",
                    "failed_at": "composer",
                    "reason": compose_output.get("error", "Composer failed"),
                    "job_id": job_id,
                }

            # G10: Video Validation
            g10 = GateVideoValidation()
            g10.evaluate(video_path=compose_output.get("video_path"))

            # Reviewer Agent
            logger.info("G10: running Reviewer agent")
            review_output = self._run_reviewer(
                job_id=job_id,
                topic=topic,
                script=script_output.get("script", []),
                caption=script_output.get("caption", ""),
                safety_rules=safety_rules,
            )

            # Package Output
            pkg_output = self._package_output(
                job_id=job_id,
                video_path=compose_output.get("video_path", ""),
                thumbnail_path=compose_output.get("thumbnail_path", ""),
                caption=script_output.get("caption", ""),
                topic=topic,
                niche=niche,
                output_dir=output_dir,
            )

            if pkg_output.get("status") == "failed":
                update_job_status(conn, job_id, "FAILED",
                                  pkg_output.get("error", "Packaging failed"))
                return {
                    "status": "failed",
                    "failed_at": "packaging",
                    "reason": pkg_output.get("error", "Packaging failed"),
                    "job_id": job_id,
                }

            update_job_status(conn, job_id, "COMPLETED")
            logger.info("Pipeline COMPLETED: job #%d", job_id)
            return {
                "status": "completed",
                "job_id": job_id,
                "output": pkg_output,
                "cost_estimate": {
                    "estimate_cents": cost_result.data.get("estimate_cents", 0.0),
                },
                "review": {
                    "score": review_output.get("score", 0),
                    "verdict": review_output.get("status", "fail"),
                },
            }

        except Exception as e:
            logger.exception("Pipeline FAILED: job #%d — %s", job_id, e)
            update_job_status(conn, job_id, "FAILED", str(e))
            return {"status": "failed", "error": str(e), "job_id": job_id}

    # ── Agent runner methods (extracted for testability) ──

    def _run_safety(self, job_id: int, topic: str,
                    **kwargs: Any) -> dict[str, Any]:
        agent = SafetyAgent()
        return agent.execute(job_id=job_id, topic=topic, **kwargs)

    def _run_researcher(self, job_id: int, topic: str,
                        safety_rules: list[str] | None = None,
                        output_dir: str = "outputs",
                        **kwargs: Any) -> dict[str, Any]:
        agent = ResearcherAgent()
        return agent.execute(job_id=job_id, topic=topic,
                             safety_rules=safety_rules or [],
                             output_dir=output_dir, **kwargs)

    def _run_scriptwriter(self, job_id: int, topic: str,
                          research_brief: str = "",
                          safety_rules: list[str] | None = None,
                          **kwargs: Any) -> dict[str, Any]:
        agent = ScriptwriterAgent()
        return agent.execute(
            job_id=job_id, topic=topic,
            research_brief=research_brief,
            safety_rules=safety_rules or [],
            **kwargs,
        )

    def _run_voice_producer(self, job_id: int,
                            script: list[dict] | None = None,
                            output_dir: str = "outputs",
                            **kwargs: Any) -> dict[str, Any]:
        agent = VoiceProducerAgent()
        return agent.execute(
            job_id=job_id, script=script or [],
            output_dir=output_dir,
            **kwargs,
        )

    def _run_visual_director(self, job_id: int,
                             script: list[dict] | None = None,
                             topic: str = "",
                             source_urls: list[str] | None = None,
                             output_dir: str = "outputs",
                             **kwargs: Any) -> dict[str, Any]:
        agent = VisualDirectorAgent()
        return agent.execute(
            job_id=job_id, script=script or [],
            topic=topic,
            source_urls=source_urls or [],
            output_dir=output_dir,
            **kwargs,
        )

    def _run_composer(self, job_id: int,
                      assets: list[dict] | None = None,
                      audio_files: list[str] | None = None,
                      output_dir: str = "outputs",
                      **kwargs: Any) -> dict[str, Any]:
        agent = ComposerAgent()
        return agent.execute(
            job_id=job_id, assets=assets or [],
            audio_files=audio_files or [],
            output_dir=output_dir,
            **kwargs,
        )

    def _run_reviewer(self, job_id: int, topic: str,
                      script: list[dict] | None = None,
                      caption: str = "",
                      safety_rules: list[str] | None = None,
                      **kwargs: Any) -> dict[str, Any]:
        agent = ReviewerAgent()
        return agent.execute(
            job_id=job_id, topic=topic,
            script=script or [],
            caption=caption,
            safety_rules=safety_rules or [],
            **kwargs,
        )

    def _package_output(self, job_id: int, video_path: str,
                        thumbnail_path: str, caption: str,
                        topic: str, niche: str,
                        output_dir: str = "outputs",
                        **kwargs: Any) -> dict[str, Any]:
        packager = OutputPackager()
        from pathlib import Path
        caption_dir = Path(output_dir) / f"job_{job_id}"
        caption_dir.mkdir(parents=True, exist_ok=True)
        caption_path_file = caption_dir / "caption.txt"
        caption_path_file.write_text(caption.strip()[:150])
        return packager.package(
            job_id=job_id,
            video_path=video_path,
            caption_path=str(caption_path_file),
            thumbnail_path=thumbnail_path,
            metadata={"topic": topic, "niche": niche},
            output_dir=output_dir,
        )
