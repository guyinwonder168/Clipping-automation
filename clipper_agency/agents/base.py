import json
from abc import ABC, abstractmethod
from typing import Any

from clipper_agency.db.connection import get_connection
from clipper_agency.db.queries import update_agent_state


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents.

    Subclasses must implement:
        agent_name  — unique identifier matching agent_states.agent_name
        execute()   — core agent logic, returns a result dict

    The run() method wraps execute() with DB state tracking:
        pending → running → completed | failed
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique agent identifier matching agent_states.agent_name."""
        ...

    @abstractmethod
    def execute(self, job_id: int, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent's core logic. Returns result dict."""
        ...

    def run(self, job_id: int, db_path: str = "data/clipper.db",
            **kwargs: Any) -> dict[str, Any]:
        """Run agent with DB state tracking.

        Updates agent_states table: pending → running → completed|failed.
        """
        conn = get_connection(db_path)
        update_agent_state(conn, job_id, self.agent_name, "running")
        try:
            result = self.execute(job_id, **kwargs)
            update_agent_state(
                conn, job_id, self.agent_name, "completed",
                output_data=json.dumps(result),
            )
            return result
        except Exception as e:
            update_agent_state(
                conn, job_id, self.agent_name, "failed",
                error_message=str(e),
            )
            return {"status": "error", "error": str(e)}
