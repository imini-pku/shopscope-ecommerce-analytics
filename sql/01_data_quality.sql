-- One row per input record; transactionid is legitimately NULL for non-purchases.
CREATE OR REPLACE TABLE parsed_events AS
SELECT source_row, try_cast(timestamp AS BIGINT) AS ts_ms,
       try_cast(visitorid AS BIGINT) AS visitor_id, event AS event_type,
       try_cast(itemid AS BIGINT) AS item_id,
       try_cast(nullif(transactionid, '') AS BIGINT) AS transaction_id,
       (try_cast(timestamp AS BIGINT) >= 0 AND try_cast(visitorid AS BIGINT) >= 0
        AND try_cast(itemid AS BIGINT) >= 0 AND event IN ('view','addtocart','transaction')
        AND (event <> 'transaction' OR try_cast(transactionid AS BIGINT) >= 0)) IS TRUE AS valid
FROM raw_events;
CREATE OR REPLACE TABLE quality_summary AS
SELECT count(*) AS raw_rows, count(*) FILTER (WHERE NOT valid) AS invalid_rows,
       count(*) FILTER (WHERE event_type <> 'transaction' AND transaction_id IS NULL) AS expected_null_transaction_ids,
       count(*) FILTER (WHERE event_type <> 'transaction' AND transaction_id IS NOT NULL) AS unexpected_transaction_ids
FROM parsed_events;
