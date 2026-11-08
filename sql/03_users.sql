CREATE OR REPLACE TABLE users AS
SELECT visitor_id, min(ts_ms) AS first_seen_ms, count(*) AS observed_events
FROM events GROUP BY visitor_id;
