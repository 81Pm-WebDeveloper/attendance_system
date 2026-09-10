"""Best-effort upload of raw device activities to a Cloudflare Worker."""

import os
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv

from config.features import D1_BACKUP_ENABLED

load_dotenv()

MAX_EVENTS_PER_REQUEST = 1000


def _connector_setting(name: str, connector: str) -> str | None:
    """Read a connector-specific setting without routing OC/CEBU to primary."""
    suffix = {"oc": "2", "cebu": "3"}.get(connector.lower(), "")
    if not suffix:
        return os.getenv(f"D1_BACKUP_{name}")

    value = os.getenv(f"D1_BACKUP_{name}{suffix}")
    # Separate Workers may deliberately share the primary backup token, but a
    # missing dedicated URL must never send OC/CEBU events to the primary D1.
    if name == "TOKEN":
        return value or os.getenv("D1_BACKUP_TOKEN")
    return value


def _backup_url(path: str, connector: str = "primary") -> str | None:
    configured = _connector_setting("URL", connector)
    if not configured:
        return None
    parts = urlsplit(configured)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _upload_events(events: list[dict], path: str, connector: str = "primary") -> dict:
    """Upload batches without making backup availability affect attendance writes."""
    if not D1_BACKUP_ENABLED:
        return {"disabled": True}

    url = _backup_url(path, connector)
    token = _connector_setting("TOKEN", connector)
    if not url or not token:
        return {"disabled": True, "reason": f"D1 backup URL or token is not configured for connector '{connector}'"}
    if not events:
        return {"uploaded": 0}

    try:
        received = inserted = 0
        for offset in range(0, len(events), MAX_EVENTS_PER_REQUEST):
            batch = events[offset:offset + MAX_EVENTS_PER_REQUEST]
            response = requests.post(
                url,
                json={"connector": connector, "events": batch},
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


def backup_attendance_payload(payload: dict, collector: str, device_id: str | None = None) -> dict:
    """Compatibility no-op: processed D1 backups were intentionally removed."""
    return {"disabled": True, "reason": "Processed D1 backups were removed; raw activities use cron_d1_backup.py"}


def backup_raw_attendance_events(events: list[dict], connector: str = "primary") -> dict:
    """Upload raw device punches to the D1 database selected by connector."""
    return _upload_events(events, "/raw-attendance-events", connector)
