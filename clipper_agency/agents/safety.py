"""Safety Agent — content safety checking via LLM."""

import json
from typing import Any

from clipper_agency.agents.base import BaseAgent
from clipper_agency.llm.client import OpenRouterClient

SAFETY_PROMPT = """You are a content safety checker. Analyze the following topic and return a JSON verdict:
- "pass": Topic is safe for content generation
- "soft_warning": Topic contains unverified claims that need cautious wording
- "hard_block": Topic involves illegal content, defamation, hate speech, or banned platform policy

Rules:
- Hard-block: illegal activities, hate speech, defamation, explicit harmful content
- Soft-warning: unverified rumors, unconfirmed news, speculative claims
- Pass: everything else (entertainment news, celebrity updates, trending topics)

Respond ONLY with valid JSON: {"verdict": "...", "reason": "..."}
"""


class SafetyAgent(BaseAgent):
    """Analyzes a topic for content safety before pipeline execution."""

    @property
    def agent_name(self) -> str:
        return "safety"

    def execute(
        self,
        job_id: int,
        topic: str = "",
        safety_rules: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        rules = safety_rules or []
        llm = OpenRouterClient()
        response = llm.chat(
            model="glm-4-9b",
            messages=[
                {"role": "system", "content": SAFETY_PROMPT},
                {
                    "role": "user",
                    "content": f"Topic: {topic}\nRules: {rules}",
                },
            ],
            temperature=0.1,
            max_tokens=256,
        )
        return self._parse_response(response["content"])

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse the JSON verdict from the LLM response."""
        try:
            stripped = content.strip().strip("```json").strip("```").strip()
            data = json.loads(stripped)
            verdict = data.get("verdict", "hard_block")
            reason = data.get("reason", "No reason given")
            if verdict == "pass":
                return {"status": "pass", "reason": reason}
            elif verdict == "soft_warning":
                return {
                    "status": "soft_warning",
                    "reason": reason,
                    "requires_cautious_wording": True,
                }
            else:
                return {"status": "hard_fail", "reason": reason}
        except (json.JSONDecodeError, KeyError) as e:
            return {"status": "hard_fail", "reason": f"Failed to parse response: {e}"}
