CREATE OR REPLACE TABLE join_checks AS
SELECT (SELECT count(*) FROM events) AS before_rows,
       (SELECT count(*) FROM events LEFT JOIN users USING(visitor_id)) AS after_rows,
       (SELECT count(*)-count(DISTINCT visitor_id) FROM users) AS duplicate_user_keys,
       (SELECT count(*) FROM events e LEFT JOIN users u USING(visitor_id) WHERE u.first_seen_ms IS NULL) AS unmatched_rows;
