-- Model and catalog are frozen before validation. No test or validation behavior is used for fitting.
CREATE OR REPLACE TABLE train_views AS
SELECT e.* FROM session_events e CROSS JOIN config c WHERE event_type='view' AND ts_ms<c.train_end_ms;
CREATE OR REPLACE TABLE popular AS
SELECT item_id,count(*) AS views,row_number() OVER(ORDER BY count(*) DESC,item_id) AS popularity_rank
FROM train_views GROUP BY item_id;
