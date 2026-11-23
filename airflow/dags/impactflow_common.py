import os
from typing import Any

import requests


def api_base_url() -> str:
    return os.environ.get(
        "IMPACTFLOW_API_BASE_URL",
        "http://host.docker.internal:8000/api/v1",
    ).rstrip("/")


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    response = requests.request(
        method,
        f"{api_base_url()}/{path.lstrip('/')}",
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def dataset_import_id(conf: dict[str, Any]) -> str:
    configured = conf.get("dataset_import_id")
    if configured:
        return str(configured)
    datasets = api_request("GET", "processing/datasets")
    for dataset in datasets:
        if dataset.get("can_process"):
            return str(dataset["import_id"])
    raise RuntimeError("No processable Bronze dataset is available.")
