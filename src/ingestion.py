import argparse
import time
from pathlib import Path

import psycopg

from src.config import DB_CONFIG, PAYSIM_CSV
from src.data_quality import validate_csv_structure


COPY_COLUMNS = """
    step,
    type,
    amount,
    name_orig,
    oldbalance_org,
    newbalance_orig,
    name_dest,
    oldbalance_dest,
    newbalance_dest,
    is_fraud,
    is_flagged_fraud
"""


COPY_SQL = f"""
COPY transactions_raw (
    {COPY_COLUMNS}
)
FROM STDIN
WITH (
    FORMAT CSV
)
"""


BLOCK_SIZE = 8 * 1024 * 1024  # 8 MiB


def get_row_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM transactions_raw"
        )
        return cur.fetchone()[0]


def copy_csv_to_postgres(
    csv_path: Path,
    replace: bool = False,
) -> None:

    validate_csv_structure(csv_path)

    file_size = csv_path.stat().st_size

    print()
    print(f"Fichier : {csv_path}")
    print(
        f"Taille  : "
        f"{file_size / 1024 / 1024:.1f} MiB"
    )

    start = time.perf_counter()

    with psycopg.connect(**DB_CONFIG) as conn:

        existing_rows = get_row_count(conn)

        if existing_rows > 0 and not replace:
            raise RuntimeError(
                f"La table contient déjà "
                f"{existing_rows:,} lignes.\n"
                "Utilisez --replace si vous voulez "
                "recharger entièrement les données."
            )

        with conn.cursor() as cur:

            if replace:
                print(
                    "Réinitialisation de "
                    "transactions_raw..."
                )
                cur.execute(
                    "TRUNCATE TABLE transactions_raw"
                )

            print("Début du COPY PostgreSQL...")

            with csv_path.open("rb") as f:

                # Le header a déjà été validé.
                # PostgreSQL reçoit uniquement les données.
                header = f.readline()

                copied_bytes = len(header)
                last_display = -1

                with cur.copy(COPY_SQL) as copy:

                    while True:
                        block = f.read(BLOCK_SIZE)

                        if not block:
                            break

                        copy.write(block)

                        copied_bytes += len(block)

                        progress = int(
                            copied_bytes
                            / file_size
                            * 100
                        )

                        if progress >= last_display + 5:
                            print(
                                f"Progression : "
                                f"{progress}%"
                            )
                            last_display = progress

            print("COPY terminé.")

            # Mise à jour des statistiques PostgreSQL
            cur.execute(
                "ANALYZE transactions_raw"
            )

        # Sortie normale du contexte :
        # la transaction est validée.

    elapsed = time.perf_counter() - start

    print()
    print(
        f"Ingestion terminée en "
        f"{elapsed:.1f} secondes."
    )


def print_database_summary() -> None:

    with psycopg.connect(**DB_CONFIG) as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(is_fraud) AS frauds,
                    SUM(is_flagged_fraud) AS flagged,
                    MIN(step) AS min_step,
                    MAX(step) AS max_step
                FROM transactions_raw
                """
            )

            (
                total,
                frauds,
                flagged,
                min_step,
                max_step,
            ) = cur.fetchone()

            print()
            print("=== Résumé PostgreSQL ===")
            print(f"Transactions : {total:,}")
            print(f"Fraudes      : {frauds:,}")
            print(f"Flaggées     : {flagged:,}")
            print(
                f"Steps         : "
                f"{min_step} → {max_step}"
            )

            cur.execute(
                """
                SELECT
                    type,
                    COUNT(*) AS transactions,
                    SUM(is_fraud) AS fraudes
                FROM transactions_raw
                GROUP BY type
                ORDER BY transactions DESC
                """
            )

            print()
            print("=== Répartition par type ===")

            for tx_type, count, frauds in cur.fetchall():
                print(
                    f"{tx_type:10s} "
                    f"{count:>10,} "
                    f"| fraudes : {frauds:,}"
                )


def main():

    parser = argparse.ArgumentParser(
        description="Ingestion du dataset PaySim"
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=PAYSIM_CSV,
        help="Chemin du CSV PaySim",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help="Vide transactions_raw avant ingestion",
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Affiche uniquement le résumé PostgreSQL",
    )

    args = parser.parse_args()

    if args.summary_only:
        print_database_summary()
        return

    copy_csv_to_postgres(
        csv_path=args.csv,
        replace=args.replace,
    )

    print_database_summary()


if __name__ == "__main__":
    main()