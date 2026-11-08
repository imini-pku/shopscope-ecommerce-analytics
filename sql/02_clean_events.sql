-- Remove exact duplicate records only; repeated browsing at different times is retained.
CREATE OR REPLACE TABLE events AS
SELECT source_row AS event_id, ts_ms, visitor_id, event_type, item_id, transaction_id,
       to_timestamp(ts_ms / 1000.0) AS event_time
FROM parsed_events WHERE valid
QUALIFY row_number() OVER (
  PARTITION BY ts_ms, visitor_id, event_type, item_id, transaction_id ORDER BY source_row
) = 1;
