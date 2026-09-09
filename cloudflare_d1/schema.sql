CREATE TABLE IF NOT EXISTS attendance_events (
  source_hash TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  collector TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  attendance_date TEXT NOT NULL,
  time_in TEXT,
  time_out TEXT,
  status TEXT,
  checkout_status TEXT,
  late_min INTEGER,
  undertime_min INTEGER,
  received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_attendance_events_employee_date
  ON attendance_events (employee_id, attendance_date);

CREATE INDEX IF NOT EXISTS idx_attendance_events_received_at
  ON attendance_events (received_at);

CREATE TABLE IF NOT EXISTS attendance_raw_events (
  source_hash TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
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
