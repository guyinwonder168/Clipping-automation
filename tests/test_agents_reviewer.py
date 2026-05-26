"""Tests for ReviewerAgent."""

import pytest

from clipper_agency.agents.reviewer import ReviewerAgent


MOCK_REVIEW_PASS = """{
  "verdict": "pass",
  "score": 85,
  "feedback": "Good script with engaging content",
  "issues": []
}"""

MOCK_REVIEW_FAIL = """{
  "verdict": "fail",
  "score": 40,
  "feedback": "Script contains unverified claims",
  "issues": ["unverified_claims", "misleading"]
}"""


class TestReviewerName:
    """Agent name property."""

    def test_reviewer_agent_name(self):
        agent = ReviewerAgent()
        assert agent.agent_name == "reviewer"


class TestReviewerParse:
    """JSON response parsing."""

    def test_parse_pass_verdict(self):
        agent = ReviewerAgent()
        result = agent._parse_review_response(MOCK_REVIEW_PASS)
        assert result["verdict"] == "pass"
        assert result["score"] == 85
        assert result["issues"] == []

    def test_parse_fail_verdict(self):
        agent = ReviewerAgent()
        result = agent._parse_review_response(MOCK_REVIEW_FAIL)
        assert result["verdict"] == "fail"
        assert result["score"] == 40
        assert len(result["issues"]) == 2

    def test_parse_with_code_fence(self):
        agent = ReviewerAgent()
        result = agent._parse_review_response(f"```json\n{MOCK_REVIEW_PASS}\n```")
        assert result["verdict"] == "pass"

    def test_parse_malformed_json(self):
        agent = ReviewerAgent()
        result = agent._parse_review_response("not json")
        assert result["verdict"] == "fail"
        assert "parse" in result["feedback"].lower()


class TestReviewerExecute:
    """Full execute() with mocked LLM."""

    @staticmethod
    def _mock_chat(content: str) -> dict:
        return {"content": content, "model": "glm-4-9b", "usage": {}}

    def test_execute_returns_pass(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_PASS),
        )
        agent = ReviewerAgent()
        result = agent.execute(
            job_id=6,
            topic="Ariana Grande",
            script=[{"scene": 1, "text": "Hey!", "duration": 3}],
            caption="Check this out!",
            safety_rules=[],
        )
        assert result["status"] == "pass"
        assert result["score"] == 85

    def test_execute_returns_fail(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_FAIL),
        )
        agent = ReviewerAgent()
        result = agent.execute(
            job_id=6,
            topic="Topic",
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            caption="Caption",
            safety_rules=[],
        )
        assert result["status"] == "fail"
        assert result["score"] == 40
        assert len(result["issues"]) == 2

    def test_execute_passes_safety_rules(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_PASS),
        )
        agent = ReviewerAgent()
        agent.execute(
            job_id=6,
            topic="Topic",
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            caption="Caption",
            safety_rules=["mark_rumors_as_unconfirmed"],
        )
        system_content = mock_chat.call_args.kwargs["messages"][0]["content"]
        assert "mark_rumors_as_unconfirmed" in system_content

    def test_execute_includes_script_and_caption(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_PASS),
        )
        agent = ReviewerAgent()
        agent.execute(
            job_id=6,
            topic="K-pop",
            script=[{"scene": 1, "text": "Script text here", "duration": 5}],
            caption="Best caption ever",
            safety_rules=[],
        )
        user_content = mock_chat.call_args.kwargs["messages"][1]["content"]
        assert "Script text here" in user_content
        assert "Best caption ever" in user_content

    def test_execute_llm_config(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_PASS),
        )
        agent = ReviewerAgent()
        agent.execute(
            job_id=6,
            topic="Topic",
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            caption="Caption",
        )
        assert mock_chat.call_args.kwargs["model"] == "glm-4-9b"
        assert mock_chat.call_args.kwargs["temperature"] == 0.2

    def test_execute_uses_prompt_file_when_available(self, mocker, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "reviewer.txt").write_text(
            "File reviewer prompt: {safety_rules_text}", encoding="utf-8"
        )
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_REVIEW_PASS),
        )
        mocker.patch("clipper_agency.agents.reviewer.PROMPTS_DIR", prompts_dir)

        ReviewerAgent().execute(
            job_id=6,
            topic="Topic",
            script=[{"scene": 1, "text": "Test", "duration": 3}],
            caption="Caption",
            safety_rules=["no_defamation"],
        )

        system_content = mock_chat.call_args.kwargs["messages"][0]["content"]
        assert system_content == "File reviewer prompt: - no_defamation"
