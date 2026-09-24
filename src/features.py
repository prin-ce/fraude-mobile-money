from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Contrat des données
# ---------------------------------------------------------------------

REQUIRED_RAW_COLUMNS = {
    "step",
    "type",
    "amount",
    "oldbalance_org",
    "oldbalance_dest",
}


# Features principales.
# Elles utilisent uniquement des informations disponibles avant transaction.
STATIC_NUMERIC_FEATURES = [
    "log_amount",
    "log_oldbalance_org",
    "log_oldbalance_dest",
    "initial_balance_zero",
    "dest_balance_zero",
    "log_ecart_vidage",
]

STATIC_CATEGORICAL_FEATURES = [
    "type",
]


# Les features temporelles sont EXPÉRIMENTALES.
TEMPORAL_FEATURES = [
    "phase_sin",
    "phase_cos",
]


def build_static_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit les features transactionnelles pré-transaction.

    Aucune information post-transaction n'est utilisée.
    """

    missing = REQUIRED_RAW_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {sorted(missing)}"
        )

    out = pd.DataFrame(index=df.index)

    amount = df["amount"].astype(float)
    oldbalance_org = df["oldbalance_org"].astype(float)
    oldbalance_dest = df["oldbalance_dest"].astype(float)

    # -------------------------------------------------------------
    # Montants / soldes
    # -------------------------------------------------------------

    out["log_amount"] = np.log1p(amount)

    out["log_oldbalance_org"] = np.log1p(
        oldbalance_org
    )

    out["log_oldbalance_dest"] = np.log1p(
        oldbalance_dest
    )

    # -------------------------------------------------------------
    # Solde émetteur nul
    # -------------------------------------------------------------

    out["initial_balance_zero"] = (
        oldbalance_org == 0
    ).astype("int8")

    # -------------------------------------------------------------
    # Solde destinataire nul
    # -------------------------------------------------------------

    out["dest_balance_zero"] = (
        oldbalance_dest == 0
    ).astype("int8")

    # -------------------------------------------------------------
    # Comportement de vidage
    # -------------------------------------------------------------

    ecart_vidage = np.where(
        oldbalance_org > 0,
        np.abs(
            amount / oldbalance_org - 1.0
        ),
        np.nan,
    )

    # Transformation logarithmique :
    # la distribution légitime présente une très longue queue.
    out["log_ecart_vidage"] = np.log1p(
        ecart_vidage
    )

    # -------------------------------------------------------------
    # Type de transaction
    # -------------------------------------------------------------

    out["type"] = df["type"].astype(str)

    return out


def prepare_xgb_matrix(
    features: pd.DataFrame,
    train_columns=None,
) -> pd.DataFrame:
    """
    Prépare la matrice numérique destinée à XGBoost.

    - One-hot encoding du type de transaction.
    - float32 pour limiter la mémoire.
    - alignement avec les colonnes utilisées à l'entraînement.
    """

    out = pd.get_dummies(
        features,
        columns=["type"],
        dtype=np.float32,
    )

    for col in out.columns:
        out[col] = out[col].astype(
            np.float32
        )

    if train_columns is not None:
        out = out.reindex(
            columns=train_columns,
            fill_value=0.0,
        )

    return out


def add_temporal_features(
    features: pd.DataFrame,
    raw_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ajoute des features temporelles expérimentales.

    Elles ne font PAS partie du modèle principal par défaut.
    """

    if "step" not in raw_df.columns:
        raise ValueError(
            "La colonne step est requise."
        )

    out = features.copy()

    phase = (
        raw_df["step"].astype(int) % 24
    )

    angle = 2.0 * np.pi * phase / 24.0

    out["phase_sin"] = np.sin(angle)
    out["phase_cos"] = np.cos(angle)

    return out