"""Best-effort upload of normalized collector events to a Cloudflare Worker."""

import hashlib
import json
import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv

from config.features import D1_BACKUP_ENABLED

load_dotenv()

MAX_EVENTS_PER_REQUEST = 1000


def _event_id(event: dict[str, Any]) -> str:
    # Collector name is metadata, not event identity. This deduplicates retries
    # even if the same device payload is replayed by another collector wrapper.
    identity = {key: value for key, value in event.items() if key != "collector"}
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _events_from_payload(payload: dict[str, Any], collector: str, device_id: str | None) -> list[dict[str, Any]]:
    events = []
    for employee_id, dates in payload.items():
        if not isinstance(dates, dict):
            continue
        for attendance_date, log_data in dates.items():
            if not isinstance(log_data, dict):
                continue
            event = {
                "device_id": device_id or "unknown",
                "collector": collector,
                "employee_id": str(employee_id),
                "attendance_date": str(attendance_date),
                "time_in": log_data.get("time-in"),
                "time_out": log_data.get("time-out"),
                "status": log_data.get("status"),
                "checkout_status": log_data.get("checkout_status"),
                "late_min": log_data.get("late_min"),
                "undertime_min": log_data.get("undertime_min"),
            }
            event["source_hash"] = _event_id(event)
            events.append(event)
    return events


def _backup_url(path: str) -> str | None:
    configured = os.getenv("D1_BACKUP_URL")
    if not configured:
        return None
    parts = urlsplit(configured)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _upload_events(events: list[dict[str, Any]], path: str) -> dict[str, Any]:
    """Upload batches without making backup availability affect attendance writes."""
    if not D1_BACKUP_ENABLED:
        return {"disabled": True}

    url = _backup_url(path)
    token = os.getenv("D1_BACKUP_TOKEN")
    if not url or not token:
        return {"disabled": True, "reason": "D1_BACKUP_URL or D1_BACKUP_TOKEN is not configured"}
    if not events:
        return {"uploaded": 0}

    try:
        received = inserted = 0
        for offset in range(0, len(events), MAX_EVENTS_PER_REQUEST):
            batch = events[offset:offset + MAX_EVENTS_PER_REQUEST]
            response = requests.post(
                url,
                json={"events": batch},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=float(os.getenv("D1_BACKUP_TIMEOUT", "10")),
            )
            response.raise_for_status()
            result = response.json()
            received += int(result.get("received", 0))
            inserted += int(result.get("inserted", 0))
        return {"ok": True, "received": received, "inserted": inserted}
    except (requests.RequestException, ValueError) as exc:
        # The primary attendance path must continue; the caller can log/retry this batch.
        return {"error": str(exc), "uploaded": 0, "events": len(events)}


def backup_attendance_payload(payload: dict[str, Any], collector: str, device_id: str | None = None) -> dict[str, Any]:
    """Upload normalized daily attendance events as a best-effort backup."""
    return _upload_events(_events_from_payload(payload, collector, device_id), "/attendance-events")


def backup_raw_attendance_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Upload unprocessed device punches as a best-effort backup."""
    return _upload_events(events, "/raw-attendance-events")
