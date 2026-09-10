-- Append-only copy of ZKTeco device activities. Do not derive, merge, or
-- resolve records from event_timestamp; use (device_id, biometric_uid) when
-- reading the original entry sequence from each device.
CREATE TABLE IF NOT EXISTS attendance_raw_events (
  source_hash TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  biometric_uid INTEGER, -- Original UID supplied by the biometric device.
  employee_id TEXT NOT NULL,
  event_timestamp TEXT NOT NULL,
  punch INTEGER,
  status INTEGER,
  verify_type INTEGER,
  workcode INTEGER,
  raw_json TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_attendance_raw_events_device_timestamp
  ON attendance_raw_events (device_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_attendance_raw_events_employee_timestamp
  ON attendance_raw_events (employee_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_attendance_raw_events_device_uid
  ON attendance_raw_events (device_id, biometric_uid);
