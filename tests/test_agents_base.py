import json

import pytest

from clipper_agency.db.connection import get_connection, close_connection
from clipper_agency.db.schema import initialize_schema
from clipper_agency.db.queries import create_job, create_agent_state
from clipper_agency.agents.base import BaseAgent


class ConcreteAgent(BaseAgent):
    """Test agent that always passes."""

    @property
    def agent_name(self) -> str:
        return "concrete_test"

    def execute(self, job_id: int, **kwargs) -> dict:
        return {"status": "pass", "output": "test_output"}


def test_agent_name():
    agent = ConcreteAgent()
    assert agent.agent_name == "concrete_test"


def test_agent_run_updates_db(temp_db_path):
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "concrete_test")

    agent = ConcreteAgent()
    result = agent.run(job_id, db_path=temp_db_path)

    assert result["status"] == "pass"
    assert result["output"] == "test_output"

    # Reconnect after WAL checkpoint
    close_connection(temp_db_path)
    conn2 = get_connection(temp_db_path)
    state = conn2.execute(
        "SELECT state, output_data FROM agent_states WHERE job_id=? AND agent_name=?",
        (job_id, "concrete_test"),
    ).fetchone()
    assert state[0] == "completed"
    assert json.loads(state[1]) == result
    close_connection(temp_db_path)


def test_agent_run_marks_failed_on_error(temp_db_path):
    conn = get_connection(temp_db_path)
    initialize_schema(conn)
    job_id = create_job(conn, topic="Test", niche="test")
    create_agent_state(conn, job_id, "failing_test")

    class FailingAgent(BaseAgent):
        @property
        def agent_name(self) -> str:
            return "failing_test"

        def execute(self, job_id: int, **kwargs) -> dict:
            raise RuntimeError("simulated failure")

    agent = FailingAgent()
    result = agent.run(job_id, db_path=temp_db_path)

    assert result["status"] == "error"
    assert "simulated failure" in result["error"]

    close_connection(temp_db_path)
    conn2 = get_connection(temp_db_path)
    state = conn2.execute(
        "SELECT state, error_message FROM agent_states WHERE job_id=? AND agent_name=?",
        (job_id, "failing_test"),
    ).fetchone()
    assert state[0] == "failed"
    assert "simulated failure" in state[1]
    close_connection(temp_db_path)


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore
