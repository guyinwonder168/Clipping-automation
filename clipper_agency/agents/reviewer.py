"""Reviewer Agent — final content quality and safety review via LLM."""

import json
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.agents.prompts import PROMPTS_DIR, load_prompt
from clipper_agency.llm.client import OpenRouterClient

REVIEWER_PROMPT = """You are a content quality reviewer for a TikTok creator channel.
Review the provided script and caption for:

1. Content quality (engagement, pacing, relevance)
2. Safety compliance (no illegal, defamatory, or harmful content)
3. Originality (not plagiarized, unique perspective)
4. Adherence to safety rules

Safety rules to enforce:
{safety_rules_text}

Return a JSON verdict:
{{
  "verdict": "pass" or "fail",
  "score": 0-100,
  "feedback": "Detailed feedback",
  "issues": ["list", "of", "issues", "if any"]
}}
"""


class ReviewerAgent(BaseAgent):
    """Reviews final content for quality, safety, and originality."""

    @property
    def agent_name(self) -> str:
        return "reviewer"

    def execute(
        self,
        job_id: int,
        topic: str = "",
        script: list[dict] | None = None,
        caption: str = "",
        safety_rules: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        rules = safety_rules or []
        safety_rules_text = "\n".join(f"- {r}" for r in rules) if rules else "None"
        scenes = script or []
        script_text = "\n".join(
            f"Scene {s.get('scene', i)}: {s.get('text', '')}"
            for i, s in enumerate(scenes)
        )

        llm = OpenRouterClient()
        prompt = load_prompt("reviewer", REVIEWER_PROMPT, PROMPTS_DIR)
        response = llm.chat(
            model="glm-4-9b",
            messages=[
                {
                    "role": "system",
                    "content": prompt.format(
                        safety_rules_text=safety_rules_text,
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic}\n\n"
                        f"Script:\n{script_text}\n\n"
                        f"Caption: {caption}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        review = self._parse_review_response(response["content"])
        return {
            "status": review["verdict"],
            "score": review["score"],
            "feedback": review["feedback"],
            "issues": review["issues"],
        }

    def _parse_review_response(self, content: str) -> dict[str, Any]:
        """Parse the JSON review response from the LLM."""
        try:
            stripped = content.strip().strip("```json").strip("```").strip()
            data = json.loads(stripped)
            return {
                "verdict": data.get("verdict", "fail"),
                "score": data.get("score", 0),
                "feedback": data.get("feedback", "No feedback"),
                "issues": data.get("issues", []),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "verdict": "fail",
                "score": 0,
                "feedback": "Failed to parse review response",
                "issues": ["parse_error"],
            }
