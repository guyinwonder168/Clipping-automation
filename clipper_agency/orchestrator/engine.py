"""Orchestrator Engine — coordinates the full gated agent pipeline."""

import json
import logging
from dataclasses import asdict
from typing import Any

from clipper_agency.agents.composer import ComposerAgent
from clipper_agency.agents.researcher import ResearcherAgent
from clipper_agency.agents.reviewer import ReviewerAgent
from clipper_agency.agents.safety import SafetyAgent
from clipper_agency.agents.scriptwriter import ScriptwriterAgent
from clipper_agency.agents.visual_director import VisualDirectorAgent
from clipper_agency.agents.voice_producer import VoiceProducerAgent
from clipper_agency.config.loader import load_settings
from clipper_agency.core.artifacts import write_json
from clipper_agency.core.manifest import (
    create_manifest,
    update_manifest_agent,
    update_manifest_final,
    update_manifest_gate,
)
from clipper_agency.core.paths import gate_result_file
from clipper_agency.core.validation import validate_agent_cache
from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import (
    PIPELINE_ORDER,
    append_audit_log,
    create_agent_state,
    create_job,
    get_agent_state,
    get_job,
    mark_agent_completed,
    mark_agent_failed,
    mark_agent_running,
    update_job_status,
)
from clipper_agency.db.schema import initialize_schema
from clipper_agency.orchestrator.gates import (
    GateResult,
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

_COMPOSER_FAILED = "Composer failed"


class Orchestrator:
    """Coordinates the full gated agent pipeline: Topic → Output Package."""

    def __init__(self, db_path: str = "data/clipper.db") -> None:
        self.db_path = db_path
        conn = get_connection(db_path)
        initialize_schema(conn)

    def _record_gate(self, assets_cache: str, job_id: int,
                     gate_name: str, result: GateResult) -> str:
        """Persist a gate result to the job workspace."""
        path = gate_result_file(assets_cache, job_id, gate_name)
        write_json(path, asdict(result))
        update_manifest_gate(assets_cache, job_id, gate_name,
                            result.passed, result.severity, path)
        return path

    def _complete_agent(self, conn, assets_cache: str, job_id: int,
                        agent_name: str) -> None:
        """Mark agent completed in DB and manifest."""
        mark_agent_completed(conn, job_id, agent_name)
        update_manifest_agent(assets_cache, job_id, agent_name, "completed")

    def _enforce_gate(self, conn, job_id: int, gate_name: str,
                      result: GateResult,
                      failed_at: str = "") -> dict[str, Any] | None:
        """Return a failure response dict if gate hard-failed, or None."""
        if not result.passed and result.severity == "hard_fail":
            logger.error("%s FAILED (hard): %s", gate_name, result.message)
            update_job_status(conn, job_id, "FAILED", result.message)
            return {
                "status": "failed",
                "failed_at": failed_at,
                "reason": result.message,
                "job_id": job_id,
            }
        return None

    def _stage_safety(
        self, conn: Any, topic: str, niche: str,
        assets_cache: str, output_dir: str,
        config_snapshot: dict | None = None,
    ) -> tuple[int, dict[str, Any]] | dict[str, Any]:
        """Run G1 preflight, create job, G2 cost, safety agent.

        Returns (job_id, cost_result) on success or a failure dict.
        """
        snapshot = config_snapshot or {}

        # G1: Input Preflight
        g1 = GateInputPreflight()
        g1_result = g1.evaluate(topic=topic, niche_config={"name": niche})
        self._record_gate(assets_cache, 0, "G1_input_preflight", g1_result)
        if not g1_result.passed:
            logger.error("G1 Preflight FAILED: %s", g1_result.message)
            update_job_status(conn, 0, "FAILED", g1_result.message)
            return {"status": "failed", "failed_at": "preflight",
                    "reason": g1_result.message, "job_id": 0}

        # Create job in DB with config snapshot
        job_id = create_job(conn, topic=topic, niche=niche,
                            config_snapshot=snapshot)
        logger.info("Job #%d created", job_id)
        create_manifest(assets_cache, job_id, topic,
                        output_dir if output_dir else "outputs",
                        config_snapshot=snapshot)
        agent_names = [
            "safety", "researcher", "scriptwriter",
            "voice_producer", "visual_director", "composer", "reviewer",
        ]
        for name in agent_names:
            create_agent_state(conn, job_id, name)

        # G2: Cost Estimate
        g2 = GateCostEstimate()
        cost_result = g2.evaluate()
        self._record_gate(assets_cache, job_id, "G2_cost_estimate", cost_result)

        # Safety Agent
        logger.info("G2: running Safety agent")
        mark_agent_running(conn, job_id, "safety")
        safety_result = self._run_safety(
            job_id=job_id, topic=topic, assets_cache=assets_cache,
        )
        if safety_result.get("status") == "hard_fail":
            logger.error("Safety FAILED: %s", safety_result.get("reason"))
            mark_agent_failed(conn, job_id, "safety", safety_result["reason"])
            update_job_status(conn, job_id, "FAILED", safety_result["reason"])
            return {
                "status": "failed", "failed_at": "safety",
                "reason": safety_result["reason"], "job_id": job_id,
            }
        self._complete_agent(conn, assets_cache, job_id, "safety")
        return job_id, cost_result

    def _stage_research(
        self, conn: Any, job_id: int, topic: str,
        safety_rules: list[str], assets_cache: str, output_dir: str,
    ) -> dict[str, Any]:
        """Run G3→Researcher→G4→G5.

        Returns research_output dict on success or a failure dict.
        """
        g3 = GateResearchCache()
        self._record_gate(assets_cache, job_id, "G3_research_cache", g3.evaluate())

        logger.info("G3: running Researcher agent")
        mark_agent_running(conn, job_id, "researcher")
        research_output = self._run_researcher(
            job_id=job_id, topic=topic, safety_rules=safety_rules,
            output_dir=output_dir, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "researcher")

        g4 = GatePostResearchRisk()
        g4_result = g4.evaluate(
            risk_flags=research_output.get("risk_flags", []),
        )
        self._record_gate(assets_cache, job_id, "G4_post_research_risk", g4_result)
        if not g4_result.passed and g4_result.severity == "hard_fail":
            update_job_status(conn, job_id, "FAILED", g4_result.message)
            return {
                "status": "failed", "failed_at": "post_research_risk",
                "reason": g4_result.message, "job_id": job_id,
            }

        g5 = GateSourceQuality()
        g5_result = g5.evaluate(
            video_sources=research_output.get("sources", []),
        )
        self._record_gate(assets_cache, job_id, "G5_source_quality", g5_result)
        if abort := self._enforce_gate(conn, job_id, "G5", g5_result,
                                        failed_at="source_quality"):
            return abort

        return research_output

    def _stage_content(
        self, conn: Any, job_id: int, topic: str,
        safety_rules: list[str], research_output: dict[str, Any],
        assets_cache: str, output_dir: str,
    ) -> tuple[dict[str, Any], dict[str, Any]] | dict[str, Any]:
        """Run G6→Scriptwriter→G7→Voice→G8.

        Returns (script_output, voice_output) on success or a failure dict.
        """
        g6 = GateCreativeMemory()
        self._record_gate(assets_cache, job_id, "G6_creative_memory", g6.evaluate())

        logger.info("G6: running Scriptwriter agent")
        mark_agent_running(conn, job_id, "scriptwriter")
        script_output = self._run_scriptwriter(
            job_id=job_id, topic=topic,
            research_brief=research_output.get("research_brief", ""),
            safety_rules=safety_rules, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "scriptwriter")

        g7 = GateScriptValidation()
        script_scenes = script_output.get("script", [])
        script_text = " ".join(
            s.get("text", "") for s in script_scenes
        ) if isinstance(script_scenes, list) else str(script_scenes)
        g7_result = g7.evaluate(
            script=script_text, caption=script_output.get("caption", ""),
        )
        self._record_gate(assets_cache, job_id, "G7_script_validation", g7_result)

        logger.info("G7: running Voice Producer agent")
        mark_agent_running(conn, job_id, "voice_producer")
        voice_output = self._run_voice_producer(
            job_id=job_id, script=script_output.get("script", []),
            output_dir=output_dir, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "voice_producer")

        g8 = GateAudioValidation()
        audio_list = voice_output.get("audio_files") or []
        first_audio = audio_list[0] if audio_list else None
        g8_result = g8.evaluate(audio_path=first_audio)
        self._record_gate(assets_cache, job_id, "G8_audio_validation", g8_result)
        if abort := self._enforce_gate(conn, job_id, "G8", g8_result,
                                        failed_at="audio_validation"):
            return abort

        return script_output, voice_output

    def _stage_composition(
        self, conn: Any, job_id: int, topic: str,
        research_output: dict[str, Any],
        script_output: dict[str, Any], voice_output: dict[str, Any],
        assets_cache: str, output_dir: str,
    ) -> dict[str, Any]:
        """Run Visual→G9→Composer→G10.

        Returns compose_output dict on success or a failure dict.
        """
        logger.info("G8: running Visual Director agent")
        mark_agent_running(conn, job_id, "visual_director")
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
            job_id=job_id, script=script_output.get("script", []),
            topic=topic, source_urls=source_urls,
            output_dir=output_dir, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "visual_director")

        g9 = GateAssetValidation()
        asset_paths = [a.get("path", "") for a in visual_output.get("assets", [])]
        g9_result = g9.evaluate(asset_paths=asset_paths)
        self._record_gate(assets_cache, job_id, "G9_asset_validation", g9_result)
        if abort := self._enforce_gate(conn, job_id, "G9", g9_result,
                                        failed_at="asset_validation"):
            return abort

        logger.info("G9: running Composer agent")
        mark_agent_running(conn, job_id, "composer")
        compose_output = self._run_composer(
            job_id=job_id, assets=visual_output.get("assets", []),
            audio_files=voice_output.get("audio_files", []),
            output_dir=output_dir, assets_cache=assets_cache,
        )

        if compose_output.get("status") == "failed":
            logger.error("Composer FAILED: %s", compose_output.get("error"))
            mark_agent_failed(conn, job_id, "composer",
                               compose_output.get("error", _COMPOSER_FAILED))
            update_job_status(conn, job_id, "FAILED",
                               compose_output.get("error", _COMPOSER_FAILED))
            return {
                "status": "failed", "failed_at": "composer",
                "reason": compose_output.get("error", _COMPOSER_FAILED),
                "job_id": job_id,
            }
        self._complete_agent(conn, assets_cache, job_id, "composer")

        g10 = GateVideoValidation()
        g10_result = g10.evaluate(video_path=compose_output.get("video_path"))
        self._record_gate(assets_cache, job_id, "G10_video_validation", g10_result)
        if abort := self._enforce_gate(conn, job_id, "G10", g10_result,
                                        failed_at="video_validation"):
            return abort

        return compose_output

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

        # Build config snapshot for retry/resume determinism
        config_snapshot = {
            "topic": topic,
            "niche": niche,
            "output_dir": output_dir,
            "assets_cache": assets_cache,
        }

        # Stage 1: Preflight + Safety
        stage1 = self._stage_safety(conn, topic, niche, assets_cache,
                                     output_dir, config_snapshot=config_snapshot)
        if isinstance(stage1, dict):
            return stage1
        job_id, cost_result = stage1

        try:
            safety_rules = ["no_defamation", "mark_rumors_as_unconfirmed"]

            # Stage 2: Research (G3→G5)
            research_output = self._stage_research(
                conn, job_id, topic, safety_rules, assets_cache, output_dir,
            )
            if isinstance(research_output, dict) and research_output.get("status") == "failed":
                return research_output

            # Stage 3: Content creation (G6→G8)
            stage3 = self._stage_content(
                conn, job_id, topic, safety_rules, research_output,
                assets_cache, output_dir,
            )
            if isinstance(stage3, dict) and stage3.get("status") == "failed":
                return stage3
            script_output, voice_output = stage3

            # Stage 4: Composition (Visual→G10)
            compose_output = self._stage_composition(
                conn, job_id, topic, research_output,
                script_output, voice_output,
                assets_cache, output_dir,
            )
            if isinstance(compose_output, dict) and compose_output.get("status") == "failed":
                return compose_output

            # Stage 5: Review + Package
            logger.info("G10: running Reviewer agent")
            mark_agent_running(conn, job_id, "reviewer")
            review_output = self._run_reviewer(
                job_id=job_id, topic=topic,
                script=script_output.get("script", []),
                caption=script_output.get("caption", ""),
                safety_rules=safety_rules,
            )
            self._complete_agent(conn, assets_cache, job_id, "reviewer")

            pkg_output = self._package_output(
                job_id=job_id,
                video_path=compose_output.get("video_path", ""),
                thumbnail_path=compose_output.get("thumbnail_path", ""),
                caption=script_output.get("caption", ""),
                topic=topic, niche=niche, output_dir=output_dir,
            )

            if pkg_output.get("status") == "failed":
                update_job_status(conn, job_id, "FAILED",
                                  pkg_output.get("error", "Packaging failed"))
                return {
                    "status": "failed", "failed_at": "packaging",
                    "reason": pkg_output.get("error", "Packaging failed"),
                    "job_id": job_id,
                }

            update_manifest_final(assets_cache, job_id, {
                "video": pkg_output.get("video_path", ""),
                "caption": pkg_output.get("caption_path", ""),
                "thumbnail": pkg_output.get("thumbnail_path", ""),
                "metadata": pkg_output.get("metadata_path", ""),
            })

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

    def _load_agent_output(self, assets_cache: str, job_id: int,
                           agent_name: str) -> dict[str, Any]:
        """Load a completed agent's output.json from the artifact workspace."""
        from clipper_agency.core.paths import agent_output_file
        from clipper_agency.core.artifacts import read_json
        path = agent_output_file(assets_cache, job_id, agent_name)
        try:
            return read_json(path)
        except (FileNotFoundError, ValueError):
            return {}

    def _try_load_cached(
        self, assets_cache: str, job_id: int, agent_name: str,
    ) -> dict[str, Any]:
        """Validate cached artifacts and return output.json if valid.

        Returns an empty dict when cache is invalid so the caller can
        fall through to re-running the agent.
        """
        vr = validate_agent_cache(assets_cache, job_id, agent_name)
        if not vr.passed:
            logger.info("Cache invalid for %s job #%d: %s",
                        agent_name, job_id, "; ".join(vr.issues))
            return {}
        return self._load_agent_output(assets_cache, job_id, agent_name)

    def run_pipeline_from(
        self, job_id: int, from_agent: str, use_cache: bool = False,
    ) -> dict[str, Any]:
        """Re-run pipeline from a specific agent, reusing completed outputs.

        Reconstructs intermediate data from persisted agent output.json files
        and skips agents that completed before ``from_agent``.
        """
        conn = get_connection(self.db_path)
        job = get_job(conn, job_id)
        if not job:
            return {"status": "failed", "reason": f"Job {job_id} not found",
                    "job_id": job_id}

        # Load config snapshot
        snapshot_raw = job.get("config_snapshot")
        snapshot = json.loads(snapshot_raw) if snapshot_raw else {}
        topic = snapshot.get("topic", job.get("topic", ""))
        niche = snapshot.get("niche", job.get("niche", "indonesian_artists"))
        output_dir = snapshot.get("output_dir", "outputs")
        assets_cache = snapshot.get("assets_cache", "")
        if not assets_cache:
            settings = load_settings()
            assets_cache = str(settings.assets_cache)

        update_job_status(conn, job_id, "RUNNING")
        append_audit_log(conn, action="pipeline_retry", actor="engine",
                         resource_type="job", resource_id=job_id,
                         details=json.dumps({"from_agent": from_agent,
                                             "use_cache": use_cache}))

        if from_agent not in PIPELINE_ORDER:
            update_job_status(conn, job_id, "FAILED",
                              f"Unknown agent: {from_agent}")
            return {"status": "failed", "reason": f"Unknown agent: {from_agent}",
                    "job_id": job_id}

        from_idx = PIPELINE_ORDER.index(from_agent)

        # Reconstruct completed upstream outputs
        research_output: dict[str, Any] = {}
        script_output: dict[str, Any] = {}
        voice_output: dict[str, Any] = {}
        visual_output: dict[str, Any] = {}

        if from_idx > PIPELINE_ORDER.index("researcher"):
            research_output = self._load_agent_output(
                assets_cache, job_id, "researcher")
        if from_idx > PIPELINE_ORDER.index("scriptwriter"):
            script_output = self._load_agent_output(
                assets_cache, job_id, "scriptwriter")
        if from_idx > PIPELINE_ORDER.index("voice_producer"):
            voice_output = self._load_agent_output(
                assets_cache, job_id, "voice_producer")
        if from_idx > PIPELINE_ORDER.index("visual_director"):
            visual_output = self._load_agent_output(
                assets_cache, job_id, "visual_director")

        safety_rules = ["no_defamation", "mark_rumors_as_unconfirmed"]

        try:
            # Stage: Research (researcher + gates G3-G5)
            if from_idx <= PIPELINE_ORDER.index("researcher"):
                research_result = self._stage_research(
                    conn, job_id, topic, safety_rules, assets_cache, output_dir,
                )
                if isinstance(research_result, dict) and research_result.get("status") == "failed":
                    return research_result
                research_output = research_result

            # Stage: Content (scriptwriter + voice + gates G6-G8)
            if from_idx <= PIPELINE_ORDER.index("scriptwriter"):
                if use_cache:
                    cached = self._try_load_cached(
                        assets_cache, job_id, "scriptwriter")
                    if cached:
                        script_output = cached
                    else:
                        script_output = self._run_content_scriptwriter(
                            conn, job_id, topic, safety_rules,
                            research_output, assets_cache,
                        )
                else:
                    script_output = self._run_content_scriptwriter(
                        conn, job_id, topic, safety_rules,
                        research_output, assets_cache,
                    )

            if from_idx <= PIPELINE_ORDER.index("voice_producer"):
                if use_cache:
                    cached = self._try_load_cached(
                        assets_cache, job_id, "voice_producer")
                    if cached:
                        voice_output = cached
                    else:
                        voice_output = self._run_content_voice(
                            conn, job_id, script_output,
                            output_dir, assets_cache,
                        )
                else:
                    voice_output = self._run_content_voice(
                        conn, job_id, script_output,
                        output_dir, assets_cache,
                    )

            # Stage: Composition (visual + composer + gates G9-G10)
            if from_idx <= PIPELINE_ORDER.index("visual_director"):
                mark_agent_running(conn, job_id, "visual_director")
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
                    job_id=job_id, script=script_output.get("script", []),
                    topic=topic, source_urls=source_urls,
                    output_dir=output_dir, assets_cache=assets_cache,
                )
                self._complete_agent(conn, assets_cache, job_id,
                                     "visual_director")

            if from_idx <= PIPELINE_ORDER.index("composer"):
                mark_agent_running(conn, job_id, "composer")
                compose_output = self._run_composer(
                    job_id=job_id,
                    assets=visual_output.get("assets", []),
                    audio_files=voice_output.get("audio_files", []),
                    output_dir=output_dir, assets_cache=assets_cache,
                )

                if compose_output.get("status") == "failed":
                    mark_agent_failed(conn, job_id, "composer",
                                       compose_output.get("error",
                                                          _COMPOSER_FAILED))
                    update_job_status(
                        conn, job_id, "FAILED",
                        compose_output.get("error", _COMPOSER_FAILED))
                    return {"status": "failed", "failed_at": "composer",
                            "reason": compose_output.get("error",
                                                          _COMPOSER_FAILED),
                            "job_id": job_id}
                self._complete_agent(conn, assets_cache, job_id, "composer")

                g10 = GateVideoValidation()
                g10_result = g10.evaluate(
                    video_path=compose_output.get("video_path"))
                self._record_gate(assets_cache, job_id,
                                  "G10_video_validation", g10_result)
                if abort := self._enforce_gate(
                    conn, job_id, "G10", g10_result,
                    failed_at="video_validation",
                ):
                    return abort
            else:
                compose_output = self._load_agent_output(
                    assets_cache, job_id, "composer")

            # Stage: Review + Package
            if from_idx <= PIPELINE_ORDER.index("reviewer"):
                mark_agent_running(conn, job_id, "reviewer")
                review_output = self._run_reviewer(
                    job_id=job_id, topic=topic,
                    script=script_output.get("script", []),
                    caption=script_output.get("caption", ""),
                    safety_rules=safety_rules,
                )
                self._complete_agent(conn, assets_cache, job_id, "reviewer")

                pkg_output = self._package_output(
                    job_id=job_id,
                    video_path=compose_output.get("video_path", ""),
                    thumbnail_path=compose_output.get("thumbnail_path", ""),
                    caption=script_output.get("caption", ""),
                    topic=topic, niche=niche, output_dir=output_dir,
                )

                if pkg_output.get("status") == "failed":
                    update_job_status(
                        conn, job_id, "FAILED",
                        pkg_output.get("error", "Packaging failed"))
                    return {"status": "failed", "failed_at": "packaging",
                            "reason": pkg_output.get("error",
                                                      "Packaging failed"),
                            "job_id": job_id}

                update_manifest_final(assets_cache, job_id, {
                    "video": pkg_output.get("video_path", ""),
                    "caption": pkg_output.get("caption_path", ""),
                    "thumbnail": pkg_output.get("thumbnail_path", ""),
                    "metadata": pkg_output.get("metadata_path", ""),
                })

            update_job_status(conn, job_id, "COMPLETED")
            logger.info("Pipeline retry COMPLETED: job #%d from %s",
                        job_id, from_agent)
            return {"status": "completed", "job_id": job_id}

        except Exception as e:
            logger.exception("Pipeline retry FAILED: job #%d — %s", job_id, e)
            update_job_status(conn, job_id, "FAILED", str(e))
            return {"status": "failed", "error": str(e), "job_id": job_id}

    def _run_content_scriptwriter(
        self, conn: Any, job_id: int, topic: str,
        safety_rules: list[str], research_output: dict[str, Any],
        assets_cache: str,
    ) -> dict[str, Any]:
        """Run scriptwriter stage of content creation."""
        g6 = GateCreativeMemory()
        self._record_gate(assets_cache, job_id, "G6_creative_memory",
                          g6.evaluate())

        mark_agent_running(conn, job_id, "scriptwriter")
        script_output = self._run_scriptwriter(
            job_id=job_id, topic=topic,
            research_brief=research_output.get("research_brief", ""),
            safety_rules=safety_rules, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "scriptwriter")

        g7 = GateScriptValidation()
        script_scenes = script_output.get("script", [])
        script_text = " ".join(
            s.get("text", "") for s in script_scenes
        ) if isinstance(script_scenes, list) else str(script_scenes)
        g7_result = g7.evaluate(
            script=script_text,
            caption=script_output.get("caption", ""),
        )
        self._record_gate(assets_cache, job_id, "G7_script_validation",
                          g7_result)

        return script_output

    def _run_content_voice(
        self, conn: Any, job_id: int,
        script_output: dict[str, Any],
        output_dir: str, assets_cache: str,
    ) -> dict[str, Any]:
        """Run voice producer stage of content creation."""
        mark_agent_running(conn, job_id, "voice_producer")
        voice_output = self._run_voice_producer(
            job_id=job_id, script=script_output.get("script", []),
            output_dir=output_dir, assets_cache=assets_cache,
        )
        self._complete_agent(conn, assets_cache, job_id, "voice_producer")

        g8 = GateAudioValidation()
        audio_list = voice_output.get("audio_files") or []
        first_audio = audio_list[0] if audio_list else None
        g8_result = g8.evaluate(audio_path=first_audio)
        self._record_gate(assets_cache, job_id, "G8_audio_validation",
                          g8_result)
        return voice_output

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
