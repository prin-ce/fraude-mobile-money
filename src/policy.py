from __future__ import annotations

import numpy as np
import pandas as pd


def expected_avoidable_loss(
    probability,
    amount,
    loss_fraction: float = 1.0,
    intervention_effectiveness: float = 1.0,
):
    """
    Perte financière évitable attendue.

    Tous les montants économiques doivent être exprimés
    dans la même unité que `amount`.
    """

    probability = np.asarray(
        probability,
        dtype=float,
    )

    amount = np.asarray(
        amount,
        dtype=float,
    )

    if not 0 <= loss_fraction <= 1:
        raise ValueError(
            "loss_fraction doit être compris entre 0 et 1."
        )

    if not 0 <= intervention_effectiveness <= 1:
        raise ValueError(
            "intervention_effectiveness doit être compris entre 0 et 1."
        )

    return (
        probability
        * amount
        * loss_fraction
        * intervention_effectiveness
    )


def expected_net_value(
    probability,
    amount,
    investigation_cost: float,
    loss_fraction: float = 1.0,
    intervention_effectiveness: float = 1.0,
):
    """
    Valeur économique attendue d'une investigation.

    EV > 0 :
        investigation économiquement justifiée
        dans le scénario considéré.
    """

    if investigation_cost < 0:
        raise ValueError(
            "investigation_cost doit être >= 0."
        )

    avoidable_loss = expected_avoidable_loss(
        probability=probability,
        amount=amount,
        loss_fraction=loss_fraction,
        intervention_effectiveness=intervention_effectiveness,
    )

    return (
        avoidable_loss
        - investigation_cost
    )


def economic_decision(
    probability,
    amount,
    investigation_cost: float,
    loss_fraction: float = 1.0,
    intervention_effectiveness: float = 1.0,
):
    """
    Retourne True lorsque l'investigation possède
    une valeur attendue strictement positive.
    """

    ev = expected_net_value(
        probability=probability,
        amount=amount,
        investigation_cost=investigation_cost,
        loss_fraction=loss_fraction,
        intervention_effectiveness=intervention_effectiveness,
    )

    return ev > 0