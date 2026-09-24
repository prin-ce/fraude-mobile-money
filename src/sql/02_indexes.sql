CREATE INDEX IF NOT EXISTS
    idx_transactions_step
ON transactions_raw(step);


CREATE INDEX IF NOT EXISTS
    idx_transactions_type
ON transactions_raw(type);


CREATE INDEX IF NOT EXISTS
    idx_transactions_is_fraud
ON transactions_raw(is_fraud);


ANALYZE transactions_raw;