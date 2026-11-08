-- A gap strictly greater than 30 minutes starts a new session.
-- event_id gives reproducible ordering of ties; tied timestamps never imply a strict funnel transition.
CREATE OR REPLACE TABLE session_events AS
WITH gaps AS (
 SELECT *, lag(ts_ms) OVER (PARTITION BY visitor_id ORDER BY ts_ms,event_id) AS previous_ms FROM events
), flags AS (
 SELECT *, CASE WHEN previous_ms IS NULL OR ts_ms-previous_ms > 1800000 THEN 1 ELSE 0 END AS new_session FROM gaps
)
SELECT *, sum(new_session) OVER (
 PARTITION BY visitor_id ORDER BY ts_ms,event_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)::BIGINT AS session_no FROM flags;
CREATE OR REPLACE TABLE sessions AS
SELECT visitor_id,session_no,min(ts_ms) AS start_ms,max(ts_ms) AS end_ms,
 count(*) AS events,count(*) FILTER (WHERE event_type='view') AS views
FROM session_events GROUP BY visitor_id,session_no;
