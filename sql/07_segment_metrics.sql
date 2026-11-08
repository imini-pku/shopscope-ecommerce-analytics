-- First observed session is not a newly registered customer.
CREATE OR REPLACE TABLE segment_metrics AS
WITH ordered_purchase AS (
 SELECT visitor_id,session_no,bool_or(purchase_ms IS NOT NULL) AS has_purchase
 FROM funnel_pairs GROUP BY ALL
)
SELECT CASE WHEN s.session_no=1 THEN '首次观测访问' ELSE '已有历史访问' END AS segment,
 count(*) AS sessions,count(*) FILTER(WHERE s.views>0) AS view_sessions,
 count(*) FILTER(WHERE o.has_purchase) AS view_purchase_sessions,
 count(*) FILTER(WHERE o.has_purchase)::DOUBLE/nullif(count(*) FILTER(WHERE s.views>0),0) AS purchase_rate
FROM sessions s LEFT JOIN ordered_purchase o USING(visitor_id,session_no) GROUP BY segment;
