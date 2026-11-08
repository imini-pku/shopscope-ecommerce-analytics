CREATE OR REPLACE TABLE recommendations AS
WITH candidates AS (
 SELECT q.query_id,'popular' AS method,p.item_id,1 AS tier,p.popularity_rank AS r
 FROM eval_queries q CROSS JOIN popular p WHERE p.popularity_rank<=20 AND p.item_id<>q.seed_item
 UNION ALL
 SELECT q.query_id,'coview',r.candidate_item,0,r.related_rank FROM eval_queries q JOIN related_top r USING(seed_item)
 UNION ALL
 SELECT q.query_id,'coview',p.item_id,1,p.popularity_rank FROM eval_queries q CROSS JOIN popular p
 WHERE p.popularity_rank<=20 AND p.item_id<>q.seed_item
), unique_candidates AS (
 SELECT * FROM candidates QUALIFY row_number() OVER(PARTITION BY query_id,method,item_id ORDER BY tier,r)=1
)
SELECT *,row_number() OVER(PARTITION BY query_id,method ORDER BY tier,r,item_id) AS rank
FROM unique_candidates QUALIFY rank<=10;
CREATE OR REPLACE TABLE evaluation_detail AS
SELECT q.query_id,q.visitor_id,q.split,q.target_item,m.method,
 max(CASE WHEN r.item_id=q.target_item THEN 1 ELSE 0 END) AS hit,
 min(r.tier) AS full_popular_fallback
FROM eval_queries q CROSS JOIN (VALUES ('popular'),('coview')) m(method)
LEFT JOIN recommendations r ON r.query_id=q.query_id AND r.method=m.method GROUP BY ALL;
CREATE OR REPLACE TABLE evaluation_metrics AS
SELECT d.split,d.method,count(*) AS queries,(SELECT count(*) FROM popular) AS candidate_items,
 sum(d.hit) AS hits,avg(d.hit) AS hit_rate_at_10,
 (SELECT count(DISTINCT r.item_id)::DOUBLE/(SELECT count(*) FROM popular)
  FROM recommendations r JOIN eval_queries q USING(query_id) WHERE q.split=d.split AND r.method=d.method) AS coverage_at_10,
 avg(d.full_popular_fallback) AS fallback_rate
FROM evaluation_detail d GROUP BY d.split,d.method ORDER BY d.split,d.method;
