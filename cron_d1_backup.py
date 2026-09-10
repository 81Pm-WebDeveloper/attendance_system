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
    timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    raw = {
        "uid": getattr(log, "uid", None),
        "user_id": str(log.user_id),
        "timestamp": timestamp,
        "punch": getattr(log, "punch", None),
        "status": getattr(log, "status", None),
        "verify_type": getattr(log, "verify_type", None),
        "workcode": getattr(log, "workcode", None),
    }
    raw = {key: value for key, value in raw.items() if value is not None}
    source_hash = hashlib.sha256(
        json.dumps({"device_id": device_id, "event": raw}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "source_hash": source_hash,
        "device_id": device_id,
        "biometric_uid": getattr(log, "uid", None),
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

    return prepare_employee_logs(employee_logs), raw_events


def _configured_devices() -> list[tuple[str, str, int]]:
    """Return both device pairs, allowing D1-specific overrides in .env."""
    candidates = [
        (
            "primary",
            os.getenv("D1_BACKUP_DEVICE_IP") or os.getenv("device_ip"),
            os.getenv("D1_BACKUP_DEVICE_PORT") or os.getenv("device_port", "4370"),
        ),
        (
            "1108",
            os.getenv("D1_BACKUP_DEVICE_IP_1108") or os.getenv("device_ip_1108"),
            os.getenv("D1_BACKUP_DEVICE_PORT_1108") or os.getenv("device_port_1108", "4370"),
        ),
    ]
    devices = []
    seen = set()
    for label, ip, port in candidates:
        if not ip:
            continue
        device = (label, ip, int(port))
        if (ip, int(port)) not in seen:
            devices.append(device)
            seen.add((ip, int(port)))
    return devices


def _backup_device(label: str, device_ip: str, device_port: int, days: int | None) -> dict:
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
        raw_result = backup_raw_attendance_events(raw_events)
        return {
            "device": label,
            "ip": device_ip,
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
