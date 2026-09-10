-- Device UID is the immutable input sequence.  Older uploads may have been
-- deduplicated by timestamp-derived hashes and can contain duplicate UIDs.
-- Retain the first received copy for each device/UID without consulting its
-- event timestamp, then prevent future duplicates at the D1 boundary.
UPDATE attendance_raw_events
SET biometric_uid = CAST(json_extract(raw_json, '$.uid') AS INTEGER)
WHERE biometric_uid IS NULL
  AND json_type(raw_json, '$.uid') = 'integer';

DELETE FROM attendance_raw_events AS duplicate
WHERE duplicate.biometric_uid IS NOT NULL
  AND EXISTS (
    SELECT 1
    FROM attendance_raw_events AS first_received
    WHERE first_received.device_id = duplicate.device_id
      AND first_received.biometric_uid = duplicate.biometric_uid
      AND first_received.rowid < duplicate.rowid
  );

DROP INDEX IF EXISTS idx_attendance_raw_events_device_uid;

CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_raw_events_device_uid
  ON attendance_raw_events (device_id, biometric_uid)
  WHERE biometric_uid IS NOT NULL;
