CREATE TABLE IF NOT EXISTS transactions_raw (

    step INTEGER NOT NULL
        CHECK (step >= 1),

    type VARCHAR(16) NOT NULL
        CHECK (
            type IN (
                'CASH_IN',
                'CASH_OUT',
                'DEBIT',
                'PAYMENT',
                'TRANSFER'
            )
        ),

    amount NUMERIC(18,2) NOT NULL
        CHECK (amount >= 0),

    name_orig VARCHAR(16) NOT NULL,

    oldbalance_org NUMERIC(18,2) NOT NULL
        CHECK (oldbalance_org >= 0),

    newbalance_orig NUMERIC(18,2) NOT NULL
        CHECK (newbalance_orig >= 0),

    name_dest VARCHAR(16) NOT NULL,

    oldbalance_dest NUMERIC(18,2) NOT NULL
        CHECK (oldbalance_dest >= 0),

    newbalance_dest NUMERIC(18,2) NOT NULL
        CHECK (newbalance_dest >= 0),

    is_fraud SMALLINT NOT NULL
        CHECK (is_fraud IN (0, 1)),

    is_flagged_fraud SMALLINT NOT NULL
        CHECK (is_flagged_fraud IN (0, 1))
);