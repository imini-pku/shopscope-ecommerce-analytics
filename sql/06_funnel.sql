-- Unit: (visitor, session, item). A pair is counted once, at strictly increasing timestamps.
CREATE OR REPLACE TABLE funnel_pairs AS
WITH viewed AS (
 SELECT visitor_id,session_no,item_id,min(ts_ms) AS first_view_ms
 FROM session_events WHERE event_type='view' GROUP BY ALL
), added AS (
 SELECT v.*,min(e.ts_ms) FILTER (WHERE e.event_type='addtocart' AND e.ts_ms>v.first_view_ms) AS add_ms
 FROM viewed v LEFT JOIN session_events e USING(visitor_id,session_no,item_id) GROUP BY ALL
)
SELECT a.*,min(e.ts_ms) FILTER (WHERE e.event_type='transaction' AND e.ts_ms>a.first_view_ms) AS purchase_ms,
 min(e.ts_ms) FILTER (WHERE e.event_type='transaction' AND e.ts_ms>a.add_ms) AS strict_purchase_ms
FROM added a LEFT JOIN session_events e USING(visitor_id,session_no,item_id) GROUP BY ALL;
CREATE OR REPLACE TABLE funnel_metrics AS
SELECT count(*) AS view_pairs,count(add_ms) AS view_add_pairs,
 count(purchase_ms) AS view_purchase_pairs,count(strict_purchase_ms) AS strict_three_step_pairs,
 count(add_ms)::DOUBLE/nullif(count(*),0) AS view_to_add_rate,
 count(purchase_ms)::DOUBLE/nullif(count(*),0) AS view_to_purchase_rate,
 count(strict_purchase_ms)::DOUBLE/nullif(count(*),0) AS strict_rate FROM funnel_pairs;
