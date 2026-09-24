-- ============================================================
-- Contrôles post-ingestion PaySim
-- ============================================================

-- 1. Vue d'ensemble
SELECT
    COUNT(*)                    AS total_transactions,
    SUM(is_fraud)               AS total_fraudes,
    SUM(is_flagged_fraud)       AS total_flagged,
    MIN(step)                   AS min_step,
    MAX(step)                   AS max_step,
    MIN(amount)                 AS min_amount,
    MAX(amount)                 AS max_amount
FROM transactions_raw;


-- 2. Répartition par type
SELECT
    type,
    COUNT(*)                    AS transactions,
    SUM(is_fraud)               AS fraudes,
    ROUND(
        100.0 * SUM(is_fraud) / COUNT(*),
        4
    )                           AS taux_fraude_pct
FROM transactions_raw
GROUP BY type
ORDER BY transactions DESC;


-- 3. Contrôle des domaines binaires
SELECT
    is_fraud,
    COUNT(*)
FROM transactions_raw
GROUP BY is_fraud
ORDER BY is_fraud;


SELECT
    is_flagged_fraud,
    COUNT(*)
FROM transactions_raw
GROUP BY is_flagged_fraud
ORDER BY is_flagged_fraud;


-- 4. Contrôle des steps
SELECT
    COUNT(DISTINCT step)        AS distinct_steps,
    MIN(step)                   AS min_step,
    MAX(step)                   AS max_step
FROM transactions_raw;


-- 5. Contrôle des valeurs nulles
SELECT
    COUNT(*) FILTER (WHERE step IS NULL)                AS null_step,
    COUNT(*) FILTER (WHERE type IS NULL)                AS null_type,
    COUNT(*) FILTER (WHERE amount IS NULL)              AS null_amount,
    COUNT(*) FILTER (WHERE name_orig IS NULL)           AS null_name_orig,
    COUNT(*) FILTER (WHERE oldbalance_org IS NULL)      AS null_oldbalance_org,
    COUNT(*) FILTER (WHERE newbalance_orig IS NULL)     AS null_newbalance_orig,
    COUNT(*) FILTER (WHERE name_dest IS NULL)           AS null_name_dest,
    COUNT(*) FILTER (WHERE oldbalance_dest IS NULL)     AS null_oldbalance_dest,
    COUNT(*) FILTER (WHERE newbalance_dest IS NULL)     AS null_newbalance_dest,
    COUNT(*) FILTER (WHERE is_fraud IS NULL)            AS null_is_fraud,
    COUNT(*) FILTER (WHERE is_flagged_fraud IS NULL)    AS null_is_flagged
FROM transactions_raw;