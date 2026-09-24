from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import MODELS_DIR
from src.features import (
    build_static_features,
    prepare_xgb_matrix,
)
from src.scoring import (
    exact_drain_mask,
    hybrid_priority_score,
    calibrated_fraud_probability,
)
from src.policy import expected_net_value


# ---------------------------------------------------------------------
# Artefacts gelés
# ---------------------------------------------------------------------

H2_MODEL_PATH = (
    MODELS_DIR
    / "h2_residual_xgb_v1.joblib"
)

ECONOMIC_MODEL_PATH = (
    MODELS_DIR
    / "economic_probability_v1.joblib"
)


H2_EXPECTED_SHA256 = (
    "6d5d5dea6d73d6f200ab2206f1aaeb5376e044b689267321acdd984d60e3ef03"
)

ECONOMIC_EXPECTED_SHA256 = (
    "77abc391b911c2c07e5b6c9410a0cd810ce898d887b4a8f3d99c929d4b6c16ed"
)


ALLOWED_TYPES = {
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
}


REQUIRED_INPUT_COLUMNS = {
    "step",
    "type",
    "amount",
    "oldbalance_org",
    "oldbalance_dest",
}


# ---------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            sha.update(block)

    return sha.hexdigest()


def validate_input_dataframe(
    df: pd.DataFrame,
) -> None:
    """
    Vérifie le contrat d'entrée pré-transaction.
    """

    missing = (
        REQUIRED_INPUT_COLUMNS
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Colonnes obligatoires manquantes : "
            f"{sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "Le jeu de transactions est vide."
        )

    if df[list(REQUIRED_INPUT_COLUMNS)].isna().any().any():
        raise ValueError(
            "Les colonnes d'entrée obligatoires "
            "ne doivent pas contenir de valeurs manquantes."
        )

    invalid_types = (
        set(df["type"].astype(str).unique())
        - ALLOWED_TYPES
    )

    if invalid_types:
        raise ValueError(
            "Types de transaction invalides : "
            f"{sorted(invalid_types)}"
        )

    if (df["step"] < 1).any():
        raise ValueError(
            "step doit être >= 1."
        )

    for col in [
        "amount",
        "oldbalance_org",
        "oldbalance_dest",
    ]:
        if (df[col] < 0).any():
            raise ValueError(
                f"{col} doit être >= 0."
            )


# ---------------------------------------------------------------------
# Service de scoring
# ---------------------------------------------------------------------

class FraudScoringService:

    def __init__(
        self,
        verify_artifacts: bool = True,
    ):
        if not H2_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Artefact H2 introuvable : "
                f"{H2_MODEL_PATH}"
            )

        if not ECONOMIC_MODEL_PATH.exists():
            raise FileNotFoundError(
                "Artefact économique introuvable : "
                f"{ECONOMIC_MODEL_PATH}"
            )

        if verify_artifacts:
            self._verify_artifacts()

        self.h2_artifact = joblib.load(
            H2_MODEL_PATH
        )

        self.economic_artifact = joblib.load(
            ECONOMIC_MODEL_PATH
        )

        self.h2_model = (
            self.h2_artifact[
                "residual_model"
            ]
        )

        self.h2_columns = (
            self.h2_artifact[
                "xgb_columns"
            ]
        )

        self.economic_model = (
            self.economic_artifact[
                "base_model"
            ]
        )

        self.economic_calibrator = (
            self.economic_artifact[
                "calibrator"
            ]
        )

        self.economic_columns = (
            self.economic_artifact[
                "xgb_columns"
            ]
        )

    def _verify_artifacts(self):
        h2_hash = sha256_file(
            H2_MODEL_PATH
        )

        economic_hash = sha256_file(
            ECONOMIC_MODEL_PATH
        )

        if h2_hash != H2_EXPECTED_SHA256:
            raise RuntimeError(
                "Le SHA-256 de l'artefact H2 "
                "ne correspond pas à l'artefact gelé."
            )

        if (
            economic_hash
            != ECONOMIC_EXPECTED_SHA256
        ):
            raise RuntimeError(
                "Le SHA-256 de l'artefact économique "
                "ne correspond pas à l'artefact gelé."
            )

    # -----------------------------------------------------------------
    # Features
    # -----------------------------------------------------------------

    def _build_features(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        validate_input_dataframe(df)

        return build_static_features(
            df
        )

    # -----------------------------------------------------------------
    # H2
    # -----------------------------------------------------------------

    def h2_scores(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        features = self._build_features(
            df
        )

        X_h2 = prepare_xgb_matrix(
            features,
            train_columns=self.h2_columns,
        )

        residual_score = (
            self.h2_model.predict_proba(
                X_h2
            )[:, 1]
        )

        exact_rule = exact_drain_mask(
            df
        )

        priority_score = (
            hybrid_priority_score(
                df,
                residual_score,
            )
        )

        return pd.DataFrame(
            {
                "exact_drain_rule":
                    exact_rule,

                "residual_ml_score":
                    residual_score,

                "h2_priority_score":
                    priority_score,
            },
            index=df.index,
        )

    # -----------------------------------------------------------------
    # Probabilité économique
    # -----------------------------------------------------------------

    def calibrated_probabilities(
        self,
        df: pd.DataFrame,
    ) -> np.ndarray:

        features = self._build_features(
            df
        )

        X_economic = (
            prepare_xgb_matrix(
                features,
                train_columns=(
                    self.economic_columns
                ),
            )
        )

        raw_probability = (
            self.economic_model
            .predict_proba(
                X_economic
            )[:, 1]
        )

        return (
            calibrated_fraud_probability(
                raw_probability,
                self.economic_calibrator,
            )
        )

    # -----------------------------------------------------------------
    # Scoring complet
    # -----------------------------------------------------------------

    def score(
        self,
        df: pd.DataFrame,
        investigation_cost: float = 100.0,
        loss_fraction: float = 1.0,
        intervention_effectiveness: float = 0.8,
    ) -> pd.DataFrame:

        validate_input_dataframe(
            df
        )

        result = df.copy()

        h2 = self.h2_scores(
            df
        )

        probabilities = (
            self.calibrated_probabilities(
                df
            )
        )

        result[
            "exact_drain_rule"
        ] = h2[
            "exact_drain_rule"
        ]

        result[
            "residual_ml_score"
        ] = h2[
            "residual_ml_score"
        ]

        result[
            "h2_priority_score"
        ] = h2[
            "h2_priority_score"
        ]

        result[
            "p_fraud_calibrated"
        ] = probabilities

        result[
            "expected_net_value"
        ] = expected_net_value(
            probability=probabilities,
            amount=result["amount"],
            investigation_cost=(
                investigation_cost
            ),
            loss_fraction=(
                loss_fraction
            ),
            intervention_effectiveness=(
                intervention_effectiveness
            ),
        )

        result[
            "economic_review"
        ] = (
            result[
                "expected_net_value"
            ] > 0
        )

        return result