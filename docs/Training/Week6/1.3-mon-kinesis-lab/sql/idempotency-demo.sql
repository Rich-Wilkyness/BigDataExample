-- PostgreSQL only. Optional isolated teaching example, not the homework table.
-- Event identity is separate from a Kinesis sequence number.
-- received_at is the INSERT statement timestamp, not proof of durable commit time.
-- Section: Group this demonstration into one database transaction
-- COMMIT makes the transaction permanent; an error should stop the script.
BEGIN;
-- Section: Isolate the learning table from application and homework tables
-- A schema is a namespace; IF NOT EXISTS permits rerunning this setup.
CREATE SCHEMA IF NOT EXISTS week6_learning;
-- Section: Declare the sink identity and timestamp contract
-- PRIMARY KEY makes duplicate event_id values impossible in this table.
-- It does not prevent duplicate transport records from reaching the consumer.
CREATE TABLE IF NOT EXISTS week6_learning.event_receipts (
    event_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    last_reported BIGINT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp()
);
-- Section: Write the first observation
-- ON CONFLICT turns a repeated identity into a no-op rather than another row.
INSERT INTO week6_learning.event_receipts (event_id, station_id, last_reported)
VALUES ('fixture-event-001', 'fixture-station-a', 1791833700)
ON CONFLICT (event_id) DO NOTHING;
-- Section: Repeat the same logical observation
-- Model a replay after a previous write committed but consumer progress did not.
INSERT INTO week6_learning.event_receipts (event_id, station_id, last_reported)
VALUES ('fixture-event-001', 'fixture-station-a', 1791833700)
ON CONFLICT (event_id) DO NOTHING;
-- Section: Verify the sink effect rather than counting write attempts
-- Two INSERT attempts should leave one row for this identity.
SELECT COUNT(*) AS rows_for_demo_identity
FROM week6_learning.event_receipts WHERE event_id = 'fixture-event-001';
-- Expected: one row for this identity, including after rerunning the script.
-- Section: Finish the database transaction
-- This commits database changes only; it does not commit a streaming checkpoint.
COMMIT;
-- Deliberately leaves the isolated demonstration row for inspection.
-- This does not implement latest-state selection, checkpoint coordination,
-- or all possible exactly-once effects. No PostgreSQL execution claimed.
