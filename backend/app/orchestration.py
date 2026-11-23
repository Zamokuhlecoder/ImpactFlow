"""Small Airflow REST client used by the ImpactFlow API.

Airflow remains the source of truth for DAG and task state; ImpactFlow stores
only the correlation and audit record needed by its own UI.
"""

from typing import Any

import httpx

from app.core.config import Settings


class OrchestrationUnavailable(RuntimeError):
    """Raised when Airflow is not configured or cannot be reached."""


class AirflowClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.airflow_base_url:
            raise OrchestrationUnavailable("Airflow is not configured.")
        self.base_url = settings.airflow_base_url.rstrip("/")
        auth = None
        if settings.airflow_username and settings.airflow_password:
            auth = (settings.airflow_username, settings.airflow_password.get_secret_value())
        self.auth = auth

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}/api/v1/{path.lstrip('/')}",
                auth=self.auth,
                json=json,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OrchestrationUnavailable(
                "The Airflow service is unavailable or returned an invalid response."
            ) from error
        if not isinstance(payload, dict):
            raise OrchestrationUnavailable("The Airflow response was not an object.")
        return payload

    def dags(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "dags", params={"limit": "100"})
        dags = payload.get("dags", [])
        return dags if isinstance(dags, list) else []

    def dag(self, dag_id: str) -> dict[str, Any]:
        return self._request("GET", f"dags/{dag_id}")

    def runs(self, dag_id: str) -> list[dict[str, Any]]:
        path = f"dags/{dag_id}/dagRuns"
        payload = self._request("GET", path, params={"limit": "100", "order_by": "-execution_date"})
        runs = payload.get("dag_runs", [])
        return runs if isinstance(runs, list) else []

    def trigger(self, dag_id: str, conf: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"dags/{dag_id}/dagRuns", json={"conf": conf})

    def tasks(self, dag_id: str, run_id: str) -> list[dict[str, Any]]:
        payload = self._request("GET", f"dags/{dag_id}/dagRuns/{run_id}/taskInstances")
        tasks = payload.get("task_instances", [])
        return tasks if isinstance(tasks, list) else []
