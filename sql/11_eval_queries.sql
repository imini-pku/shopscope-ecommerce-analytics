-- One prediction at the first view of each held-out session.
-- Label: next strictly later view of a different item in the same session.
-- Unseen labels remain in the denominator; unlabelled sessions are explicitly reported separately.
CREATE OR REPLACE TABLE prediction_points AS
SELECT e.visitor_id,e.session_no,e.item_id AS seed_item,e.ts_ms AS prediction_ms,
 CASE WHEN e.ts_ms<c.validation_end_ms THEN 'validation' ELSE 'test' END AS split
FROM session_events e JOIN sessions s USING(visitor_id,session_no) CROSS JOIN config c
WHERE e.event_type='view' AND s.start_ms>=c.train_end_ms
QUALIFY row_number() OVER(PARTITION BY e.visitor_id,e.session_no ORDER BY e.ts_ms,e.event_id)=1;
CREATE OR REPLACE TABLE eval_queries AS
SELECT p.*,e.item_id AS target_item,e.ts_ms AS target_ms,
       p.visitor_id::VARCHAR||'-'||p.session_no::VARCHAR AS query_id
FROM prediction_points p JOIN session_events e USING(visitor_id,session_no) CROSS JOIN config c
WHERE e.event_type='view' AND e.ts_ms>p.prediction_ms AND e.item_id<>p.seed_item
 AND (p.split='test' OR e.ts_ms<c.validation_end_ms)
QUALIFY row_number() OVER(PARTITION BY p.visitor_id,p.session_no ORDER BY e.ts_ms,e.event_id)=1;
