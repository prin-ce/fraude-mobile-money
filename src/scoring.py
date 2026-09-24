from __future__ import annotations

import numpy as np
import pandas as pd


def exact_drain_mask(
    df: pd.DataFrame,
) -> np.ndarray:
    """
    Identifie un vidage exact à la précision monétaire.

    La comparaison est effectuée en centimes afin d'éviter
    une dépendance à l'égalité flottante.
    """

    required = {
        "amount",
        "oldbalance_org",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    amount_cents = np.rint(
        df["amount"].to_numpy(dtype=float)
        * 100
    ).astype(np.int64)

    balance_cents = np.rint(
        df["oldbalance_org"].to_numpy(dtype=float)
        * 100
    ).astype(np.int64)

    return (
        (balance_cents > 0)
        & (amount_cents == balance_cents)
    )


def hybrid_priority_score(
    raw_df: pd.DataFrame,
    residual_scores,
) -> np.ndarray:
    """
    Score de priorité H2.

    Les transactions à vidage exact sont systématiquement
    classées avant les transactions résiduelles.

    Ce score est un score de RANKING.
    Il ne doit pas être interprété comme une probabilité.
    """

    residual_scores = np.asarray(
        residual_scores,
        dtype=float,
    )

    if len(raw_df) != len(residual_scores):
        raise ValueError(
            "raw_df et residual_scores "
            "doivent avoir la même longueur."
        )

    exact = exact_drain_mask(raw_df)

    return np.where(
        exact,
        2.0 + residual_scores,
        residual_scores,
    )


def probability_to_logit(p):
    """
    Convertit une probabilité en logit
    avec protection numérique.
    """

    p = np.asarray(
        p,
        dtype=float,
    )

    eps = 1e-7

    p = np.clip(
        p,
        eps,
        1.0 - eps,
    )

    return np.log(
        p / (1.0 - p)
    )


def calibrated_fraud_probability(
    base_scores,
    calibrator,
):
    """
    Transforme les probabilités brutes
    du modèle en probabilités calibrées.

    Contrairement au score H2, cette sortie
    est destinée à une interprétation
    probabiliste.
    """

    logits = probability_to_logit(
        base_scores
    ).reshape(-1, 1)

    return calibrator.predict_proba(
        logits
    )[:, 1]