"""Tests for ScriptwriterAgent."""

from unittest.mock import MagicMock
import pytest

from clipper_agency.agents.scriptwriter import ScriptwriterAgent


MOCK_SCRIPT_RESPONSE = """{
  "script": [{"scene": 1, "text": "Hey TikTok!", "duration": 3}],
  "caption": "Check this out! #viral",
  "hashtags": ["#viral", "#trending"],
  "estimated_duration": 60
}"""


class TestScriptwriterName:
    """Agent name property."""

    def test_scriptwriter_agent_name(self):
        agent = ScriptwriterAgent()
        assert agent.agent_name == "scriptwriter"


class TestScriptwriterParse:
    """JSON response parsing from LLM."""

    def test_parse_script_json(self):
        agent = ScriptwriterAgent()
        result = agent._parse_script_response(MOCK_SCRIPT_RESPONSE)
        assert result["script"][0]["text"] == "Hey TikTok!"
        assert result["caption"] == "Check this out! #viral"
        assert result["hashtags"] == ["#viral", "#trending"]
        assert result["estimated_duration"] == 60

    def test_parse_with_code_fence(self):
        agent = ScriptwriterAgent()
        result = agent._parse_script_response(f"```json\n{MOCK_SCRIPT_RESPONSE}\n```")
        assert result["script"][0]["text"] == "Hey TikTok!"

    def test_parse_malformed_json_returns_empty(self):
        agent = ScriptwriterAgent()
        result = agent._parse_script_response("not valid json")
        assert result["script"] == []
        assert result["caption"] == ""


class TestScriptwriterExecute:
    """Full execute() with mocked LLM."""

    @staticmethod
    def _mock_chat(content: str) -> dict:
        return {"content": content, "model": "glm-4-9b", "usage": {}}

    def test_execute_generates_script(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_SCRIPT_RESPONSE),
        )
        agent = ScriptwriterAgent()
        result = agent.execute(
            job_id=3,
            topic="Ariana Grande new album",
            research_brief="She is releasing a new album next month",
        )
        assert result["status"] == "completed"
        assert result["script"][0]["text"] == "Hey TikTok!"
        assert result["caption"] == "Check this out! #viral"
        assert result["hashtags"] == ["#viral", "#trending"]

    def test_execute_includes_research_brief_in_prompt(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_SCRIPT_RESPONSE),
        )
        agent = ScriptwriterAgent()
        agent.execute(
            job_id=3,
            topic="Topic X",
            research_brief="Research about Topic X",
        )
        messages = mock_chat.call_args.kwargs["messages"]
        user_content = messages[1]["content"]
        assert "Research about Topic X" in user_content

    def test_execute_passes_safety_rules(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_SCRIPT_RESPONSE),
        )
        agent = ScriptwriterAgent()
        agent.execute(
            job_id=3,
            topic="Topic",
            research_brief="Brief",
            safety_rules=["mark_rumors_as_unconfirmed"],
        )
        messages = mock_chat.call_args.kwargs["messages"]
        system_content = messages[0]["content"]
        assert "mark_rumors_as_unconfirmed" in system_content

    def test_execute_model_and_temperature(self, mocker):
        mock_chat = mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_SCRIPT_RESPONSE),
        )
        agent = ScriptwriterAgent()
        agent.execute(job_id=3, topic="Topic", research_brief="Brief")
        assert mock_chat.call_args.kwargs["model"] == "glm-4-9b"
        assert mock_chat.call_args.kwargs["temperature"] == 0.7

    def test_execute_handles_llm_failure(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat("NOT VALID JSON AT ALL"),
        )
        agent = ScriptwriterAgent()
        result = agent.execute(
            job_id=3,
            topic="Topic",
            research_brief="Brief",
        )
        assert result["status"] == "completed"
        assert result["script"] == []
        assert result["caption"] == ""

    def test_execute_returns_scene_list(self, mocker):
        mocker.patch(
            "clipper_agency.llm.client.OpenRouterClient.chat",
            return_value=self._mock_chat(MOCK_SCRIPT_RESPONSE),
        )
        agent = ScriptwriterAgent()
        result = agent.execute(job_id=3, topic="Topic", research_brief="B")
        assert isinstance(result["script"], list)
        assert len(result["script"]) == 1
        assert "scene" in result["script"][0]
        assert "text" in result["script"][0]
        assert "duration" in result["script"][0]
