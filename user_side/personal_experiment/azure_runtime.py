"""Azure Functions persistence for the simulation-only experiment."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

RUN_ROOT = Path(os.environ.get("SCALPING_RUN_ROOT", "/tmp/scalping_v1"))
OUTPUT_ROOT = Path(os.environ.get("SCALPING_OUTPUT_ROOT", "/tmp/scalping_output"))
CONTAINER = os.environ.get("SCALPING_STATE_CONTAINER", "scalping-v1-state")
CONNECTION_SETTING = os.environ.get("SCALPING_STORAGE_CONNECTION_SETTING", "AzureWebJobsStorage")

STATE_FILES = (
    "portfolio_state.json", "trade_log.csv", "daily_performance.csv", "decision_log.jsonl", "api_costs.csv",
    "baseline_portfolio_state.json", "baseline_trade_log.csv", "baseline_daily_performance.csv", "baseline_decision_log.jsonl",
    "adaptive_config.json", "weekly_evaluations.jsonl", "improvement_metrics.csv", "strategy_versions.csv",
)


def _service() -> BlobServiceClient:
    conn = os.environ.get(CONNECTION_SETTING)
    if not conn:
        raise RuntimeError(f"Missing Azure Storage connection setting: {CONNECTION_SETTING}")
    return BlobServiceClient.from_connection_string(conn)


def ensure_container():
    container = _service().get_container_client(CONTAINER)
    try:
        container.create_container()
    except Exception as exc:
        try:
            container.get_container_properties()
        except Exception:
            raise exc
    return container


def sync_down() -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    container = ensure_container()
    for name in STATE_FILES:
        blob = container.get_blob_client(f"state/{name}")
        try:
            RUN_ROOT.joinpath(name).write_bytes(blob.download_blob().readall())
        except ResourceNotFoundError:
            logging.info("No Azure state blob yet for %s; initializer will create it.", name)
    for blob in container.list_blobs(name_starts_with="reports/"):
        rel = blob.name.removeprefix("reports/")
        target = OUTPUT_ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(container.get_blob_client(blob.name).download_blob().readall())


def sync_up() -> None:
    container = ensure_container()
    for name in STATE_FILES:
        path = RUN_ROOT / name
        if path.exists():
            container.get_blob_client(f"state/{name}").upload_blob(path.read_bytes(), overwrite=True)
    if OUTPUT_ROOT.exists():
        for path in OUTPUT_ROOT.rglob("*"):
            if path.is_file():
                rel = path.relative_to(OUTPUT_ROOT).as_posix()
                container.get_blob_client(f"reports/{rel}").upload_blob(path.read_bytes(), overwrite=True)
