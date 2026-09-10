-- Append-only copy of ZKTeco device activities.  biometric_uid is the UID
-- assigned by the device when it receives an entry, so (device_id,
-- biometric_uid) is both the identity and the only sequence/order key.
-- event_timestamp is retained as source data only; never use it to order or
-- deduplicate raw device entries.
CREATE TABLE IF NOT EXISTS attendance_raw_events (
  source_hash TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  biometric_uid INTEGER NOT NULL, -- Original UID supplied by the biometric device.
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_raw_events_device_uid
  ON attendance_raw_events (device_id, biometric_uid);
