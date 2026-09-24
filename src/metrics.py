from __future__ import annotations

import numpy as np
import pandas as pd


def precision_recall_at_k(
    y_true,
    scores,
    k: int,
) -> dict:
    """
    Calcule Precision@K et Recall@K à partir
    d'un score de ranking.

    Les K transactions ayant les scores les plus
    élevés sont considérées comme prioritaires.
    """

    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    if len(y_true) != len(scores):
        raise ValueError(
            "y_true et scores doivent avoir "
            "la même longueur."
        )

    if k <= 0:
        raise ValueError(
            "k doit être strictement positif."
        )

    if k > len(y_true):
        raise ValueError(
            "k ne peut pas dépasser "
            "le nombre d'observations."
        )

    result = pd.DataFrame({
        "y": y_true,
        "score": scores,
    })

    result = result.sort_values(
        "score",
        ascending=False,
        kind="mergesort",
    )

    top = result.head(k)

    tp = int(
        top["y"].sum()
    )

    total_positive = int(
        result["y"].sum()
    )

    precision = (
        tp / k
    )

    recall = (
        tp / total_positive
        if total_positive > 0
        else 0.0
    )

    return {
        "k": k,
        "tp": tp,
        "precision": precision,
        "recall": recall,
    }