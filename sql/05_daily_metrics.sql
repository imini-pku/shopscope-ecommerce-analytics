CREATE OR REPLACE TABLE daily_metrics AS
SELECT strftime(event_time,'%Y-%m-%d') AS date,
 count(*) FILTER (WHERE event_type='view') AS views,
 count(*) FILTER (WHERE event_type='addtocart') AS addtocarts,
 count(*) FILTER (WHERE event_type='transaction') AS transactions,
 count(DISTINCT visitor_id) AS visitors
FROM events GROUP BY date ORDER BY date;
