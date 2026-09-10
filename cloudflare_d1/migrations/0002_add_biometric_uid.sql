ALTER TABLE attendance_raw_events ADD COLUMN biometric_uid INTEGER;

UPDATE attendance_raw_events
SET biometric_uid = CAST(json_extract(raw_json, '$.uid') AS INTEGER)
WHERE biometric_uid IS NULL
  AND json_extract(raw_json, '$.uid') IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_attendance_raw_events_device_uid
  ON attendance_raw_events (device_id, biometric_uid);
