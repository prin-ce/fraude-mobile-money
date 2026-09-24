WITH split AS (
    SELECT
        CASE
            WHEN step <= 323 THEN 'TRAIN'
            WHEN step <= 377 THEN 'VALIDATION'
            ELSE 'TEST'
        END AS segment,
        step,
        is_fraud
    FROM transactions_raw
)
SELECT
    segment,
    COUNT(*) AS transactions,
    SUM(is_fraud) AS fraudes,
    ROUND(
        100.0 * SUM(is_fraud) / COUNT(*),
        4
    ) AS taux_fraude_pct,
    MIN(step) AS min_step,
    MAX(step) AS max_step,
    COUNT(DISTINCT step) AS nb_steps
FROM split
GROUP BY segment
ORDER BY MIN(step);