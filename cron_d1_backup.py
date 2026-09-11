"""Standalone ZKTeco -> Cloudflare D1 backup collector.

This job deliberately does not call the primary Attendance API. Run it as a
separate, offset scheduled task when an independent device read is required.
"""

from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import time

from dotenv import load_dotenv

from config.features import D1_BACKUP_ENABLED
from services.d1_backup import backup_raw_attendance_events
from cron2 import connect_to_device, prepare_employee_logs, time_status, timeout_status

load_dotenv()


def _raw_event(log, device_id: str) -> dict:
    """Preserve the original ZKTeco activity fields without attendance rules."""
    # ZKTeco assigns this UID as it accepts the activity.  It is the only
    # sequence key we use for identity and ordering; device timestamps can be
    # corrected, duplicated, or arrive out of order.
    try:
        biometric_uid = int(getattr(log, "uid"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Attendance log from {device_id} has no valid device UID") from exc
    if biometric_uid < 0:
        raise ValueError(f"Attendance log from {device_id} has a negative device UID: {biometric_uid}")

    timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    raw = {
        "uid": biometric_uid,
        "user_id": str(log.user_id),
        "timestamp": timestamp,
        "punch": getattr(log, "punch", None),
        "status": getattr(log, "status", None),
        "verify_type": getattr(log, "verify_type", None),
        "workcode": getattr(log, "workcode", None),
    }
    raw = {key: value for key, value in raw.items() if value is not None}
    source_hash = hashlib.sha256(
        json.dumps(
            {"device_id": device_id, "biometric_uid": biometric_uid},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "source_hash": source_hash,
        "device_id": device_id,
        "biometric_uid": biometric_uid,
        "employee_id": str(log.user_id),
        "event_timestamp": timestamp,
        "punch": getattr(log, "punch", None),
        "status": getattr(log, "status", None),
        "verify_type": getattr(log, "verify_type", None),
        "workcode": getattr(log, "workcode", None),
        "raw_json": json.dumps(raw, sort_keys=True, separators=(",", ":")),
    }


def fetch_logs_for_backup(conn, days: int | None, device_id: str) -> tuple[dict, list[dict]]:
    today = date.today()
    start_date = today if days == 0 else (today - timedelta(days=days) if days is not None else None)
    logs = conn.get_attendance()
    if not logs:
        return {}, []

    employee_logs = {}
    raw_events = []
    for log in logs:
        log_date = log.timestamp.date()
        if days is not None and not start_date <= log_date <= today:
            continue

        raw_events.append(_raw_event(log, device_id))

        employee_id = log.user_id
        timestamp = log.timestamp.strftime("%H:%M:%S")
        punch = "time-in" if log.punch == 0 else "time-out"
        employee_logs.setdefault(employee_id, {})
        employee_logs[employee_id].setdefault(log_date, {
            "time-in": None,
            "time-out": None,
            "status": None,
            "checkout_status": "No info",
            "late_min": None,
            "undertime_min": None,
        })
        record = employee_logs[employee_id][log_date]

        if punch == "time-in" and record["time-in"] is None:
            record["time-in"] = timestamp
            result = time_status(datetime.strptime(timestamp, "%H:%M:%S").time())
            if isinstance(result, tuple):
                record["late_min"], record["status"] = result
            else:
                record["status"] = result
        elif punch == "time-out" and record["time-in"]:
            record["time-out"] = timestamp
            time_in = datetime.strptime(record["time-in"], "%H:%M:%S").time()
            time_out = datetime.strptime(timestamp, "%H:%M:%S").time()
            result = timeout_status(
                time_in,
                time_out,
                log_date.strftime("%A") == "Friday",
                log_date.strftime("%A") == "Saturday",
                False,  # voucher flow is disabled and this job has no voucher dependency
            )
            if isinstance(result, tuple):
                record["undertime_min"], record["checkout_status"] = result
            elif result:
                record["checkout_status"] = result

    # The device UID is its append/input sequence.  Do not let a corrected or
    # out-of-order timestamp change the order uploaded to D1.
    raw_events.sort(key=lambda event: event["biometric_uid"])
    return prepare_employee_logs(employee_logs), raw_events


def _configured_devices() -> list[tuple[str, str, int, str]]:
    """Return configured D1 device connectors without changing legacy names.

    In addition to the original primary and 1108 pairs, a new device can use
    D1_BACKUP_DEVICE_IP_<LABEL> and D1_BACKUP_DEVICE_PORT_<LABEL>.  Labels are
    read from the environment, so a new connector does not require code edits.
    OC and CEBU use dedicated, self-contained variable groups so one site's
    device settings cannot be mistaken for the other's.
    """
    candidates = [
        (
            "primary",
            os.getenv("D1_BACKUP_DEVICE_IP") or os.getenv("device_ip"),
            os.getenv("D1_BACKUP_DEVICE_PORT") or os.getenv("device_port", "4370"),
            "primary",
        ),
        (
            "1108",
            os.getenv("D1_BACKUP_DEVICE_IP_1108") or os.getenv("device_ip_1108"),
            os.getenv("D1_BACKUP_DEVICE_PORT_1108") or os.getenv("device_port_1108", "4370"),
            "primary",
        ),
    ]

    # Dedicated sites are intentionally read before the extensible legacy
    # pattern.  The fallback keeps existing scheduled-task environments valid
    # while deployments move to D1_BACKUP_<SITE>_DEVICE_* names.
    for site, connector in (("OC", "oc"), ("CEBU", "cebu")):
        ip = (
            os.getenv(f"D1_BACKUP_{site}_DEVICE_IP")
            or os.getenv(f"D1_BACKUP_DEVICE_IP_{site}")
        )
        if not ip:
            continue
        port = (
            os.getenv(f"D1_BACKUP_{site}_DEVICE_PORT")
            or os.getenv(f"D1_BACKUP_DEVICE_PORT_{site}")
            or "4370"
        )
        site_connector = (
            os.getenv(f"D1_BACKUP_{site}_CONNECTOR")
            or os.getenv(f"D1_BACKUP_DEVICE_CONNECTOR_{site}")
            or connector
        ).strip().lower()
        if site_connector not in {"primary", "oc", "cebu"}:
            raise ValueError(
                f"Invalid D1 backup connector for {site}: {site_connector!r}. "
                "Use primary, oc, or cebu."
            )
        candidates.append((site.lower(), ip, port, site_connector))

    connector_prefix = "D1_BACKUP_DEVICE_IP_"
    for key in sorted(os.environ):
        if not key.startswith(connector_prefix):
            continue
        label = key[len(connector_prefix):]
        if label in {"OC", "CEBU"} and os.getenv(f"D1_BACKUP_{label}_DEVICE_IP"):
            # A site was already configured through its dedicated variable
            # group; do not collect the same device twice through a fallback.
            continue
        ip = os.getenv(key)
        if not label or not ip:
            continue
        port = os.getenv(f"D1_BACKUP_DEVICE_PORT_{label}", "4370")
        connector = os.getenv(f"D1_BACKUP_DEVICE_CONNECTOR_{label}", "primary").strip().lower()
        candidates.append((label.lower(), ip, port, connector))

    devices = []
    seen = {}
    for label, ip, port, connector in candidates:
        if not ip:
            continue
        try:
            device_port = int(port)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid D1 backup port for device '{label}': {port!r}") from exc
        device = (label, ip, device_port, connector)
        endpoint = (ip, device_port)
        if endpoint not in seen:
            devices.append(device)
            seen[endpoint] = (label, connector)
        elif seen[endpoint][1] != connector:
            existing_label, existing_connector = seen[endpoint]
            raise ValueError(
                f"D1 backup devices '{existing_label}' and '{label}' use the same endpoint "
                f"but different connectors ({existing_connector!r} and {connector!r})"
            )
    return devices


def _backup_device(label: str, device_ip: str, device_port: int, connector: str, days: int | None) -> dict:
    """Read and upload one device without sharing its connection with another job."""
    try:
        conn = connect_to_device(device_ip, device_port)
        try:
            payload, raw_events = fetch_logs_for_backup(conn, days, device_ip)
        finally:
            try:
                conn.enable_device()
            finally:
                conn.disconnect()

        if not raw_events:
            return {"device": label, "ip": device_ip, "uploaded": 0, "message": "No attendance logs"}
        raw_result = backup_raw_attendance_events(raw_events, connector)
        return {
            "device": label,
            "ip": device_ip,
            "connector": connector,
            "raw": raw_result,
        }
    except Exception as exc:
        return {"device": label, "ip": device_ip, "error": str(exc)}


def run_backup() -> dict:
    if not D1_BACKUP_ENABLED:
        return {"disabled": True, "reason": "Set ENABLE_D1_BACKUP=true to run the D1 backup"}

    configured_days = os.getenv("D1_BACKUP_DAYS", "1").strip().lower()
    days = None if configured_days == "all" else max(0, int(configured_days))
    devices = _configured_devices()
    if not devices:
        return {"error": "No device_ip/device_ip_1108 pair is configured"}

    # Each device has an independent network connection, so collect and upload
    # them concurrently. executor.map retains the configured-device order.
    with ThreadPoolExecutor(max_workers=len(devices), thread_name_prefix="d1-backup") as executor:
        results = list(executor.map(lambda device: _backup_device(*device, days), devices))

    return {"devices": results}


if __name__ == "__main__":
    started = time.time()
    try:
        result = run_backup()
        print(result)
    except Exception as exc:
        print(f"D1 backup collector failed: {exc}")
    finally:
        print(f"Total execution time: {time.time() - started:.2f} seconds")
