import csv
from pathlib import Path


EXPECTED_HEADER = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]


VALID_TYPES = {
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
}


def validate_csv_structure(
    csv_path: Path,
    sample_rows: int = 1000,
) -> None:
    """Contrôle rapide avant ingestion complète."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV introuvable : {csv_path}"
        )

    if not csv_path.is_file():
        raise ValueError(
            f"Le chemin n'est pas un fichier : {csv_path}"
        )

    with csv_path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.reader(f)

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Le CSV est vide.")

        if header != EXPECTED_HEADER:
            raise ValueError(
                "En-tête PaySim inattendu.\n"
                f"Attendu : {EXPECTED_HEADER}\n"
                f"Trouvé  : {header}"
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            if row_number > sample_rows + 1:
                break

            if len(row) != len(EXPECTED_HEADER):
                raise ValueError(
                    f"Ligne {row_number} : "
                    f"{len(row)} colonnes au lieu de "
                    f"{len(EXPECTED_HEADER)}"
                )

            (
                step,
                tx_type,
                amount,
                name_orig,
                oldbalance_org,
                newbalance_orig,
                name_dest,
                oldbalance_dest,
                newbalance_dest,
                is_fraud,
                is_flagged_fraud,
            ) = row

            step = int(step)
            amount = float(amount)
            is_fraud = int(is_fraud)
            is_flagged_fraud = int(is_flagged_fraud)

            if step < 1:
                raise ValueError(
                    f"Ligne {row_number} : step invalide"
                )

            if tx_type not in VALID_TYPES:
                raise ValueError(
                    f"Ligne {row_number} : "
                    f"type inconnu {tx_type}"
                )

            if amount < 0:
                raise ValueError(
                    f"Ligne {row_number} : "
                    f"montant négatif"
                )

            if is_fraud not in (0, 1):
                raise ValueError(
                    f"Ligne {row_number} : "
                    f"isFraud invalide"
                )

            if is_flagged_fraud not in (0, 1):
                raise ValueError(
                    f"Ligne {row_number} : "
                    f"isFlaggedFraud invalide"
                )

    print(
        f"Pré-contrôle réussi : "
        f"{min(sample_rows, row_number - 1)} lignes vérifiées."
    )