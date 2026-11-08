-- Cap each training session at its first 50 distinct viewed items to bound pair expansion.
-- Full train data still supplies popularity and the candidate catalog.
CREATE OR REPLACE TABLE train_session_items AS
SELECT visitor_id,session_no,item_id,min(ts_ms) AS first_ms
FROM train_views GROUP BY visitor_id,session_no,item_id
QUALIFY row_number() OVER(PARTITION BY visitor_id,session_no ORDER BY min(ts_ms),item_id)<=50;
CREATE OR REPLACE TABLE item_session_counts AS SELECT item_id,count(*) AS n FROM train_session_items GROUP BY item_id;
CREATE OR REPLACE TABLE coview AS
WITH pairs AS (
 SELECT a.item_id AS seed_item,b.item_id AS candidate_item,count(*) AS support
 FROM train_session_items a JOIN train_session_items b USING(visitor_id,session_no)
 WHERE a.item_id<>b.item_id GROUP BY a.item_id,b.item_id HAVING count(*)>=2
)
SELECT p.*,p.support/sqrt(a.n::DOUBLE*b.n) AS score
FROM pairs p JOIN item_session_counts a ON a.item_id=p.seed_item
JOIN item_session_counts b ON b.item_id=p.candidate_item;
CREATE OR REPLACE TABLE related_top AS
SELECT *,row_number() OVER(PARTITION BY seed_item ORDER BY score DESC,support DESC,candidate_item) AS related_rank
FROM coview QUALIFY related_rank<=10;
