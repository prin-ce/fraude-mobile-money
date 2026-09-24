WITH per_step AS (
    SELECT
        step,
        COUNT(*) AS n_transactions,
        SUM(is_fraud) AS n_fraudes
    FROM transactions_raw
    GROUP BY step
),
cumulative AS (
    SELECT
        step,
        n_transactions,
        n_fraudes,

        SUM(n_transactions) OVER (
            ORDER BY step
        ) AS transactions_cumulees,

        SUM(n_fraudes) OVER (
            ORDER BY step
        ) AS fraudes_cumulees,

        SUM(n_transactions) OVER () AS total_transactions
    FROM per_step
)
SELECT
    step,
    n_transactions,
    n_fraudes,
    transactions_cumulees,
    ROUND(
        100.0 * transactions_cumulees / total_transactions,
        2
    ) AS pct_transactions_cumulees
FROM cumulative
WHERE
    transactions_cumulees >= total_transactions * 0.68
    AND
    transactions_cumulees <= total_transactions * 0.87
ORDER BY step;