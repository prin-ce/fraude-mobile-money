from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from src.config import (
    DATABASE_URL,
    PROCESSED_DATA_DIR,
    TRAIN_END_STEP,
    VALIDATION_END_STEP,
)


CHUNK_SIZE = 250_000


EXPECTED = {
    "train": {
        "rows": 4_463_587,
        "frauds": 3_643,
        "min_step": 1,
        "max_step": 323,
    },
    "validation": {
        "rows": 943_289,
        "frauds": 560,
        "min_step": 324,
        "max_step": 377,
    },
}


SELECT_COLUMNS = """
    step,
    type,
    amount::double precision AS amount,
    name_orig,
    oldbalance_org::double precision AS oldbalance_org,
    name_dest,
    oldbalance_dest::double precision AS oldbalance_dest,
    is_fraud::smallint AS is_fraud
"""


def validate_existing_target(path: Path) -> None:
    """
    Refuse d'écraser silencieusement un fichier final existant.
    """
    if path.exists():
        raise FileExistsError(
            f"{path} existe déjà. "
            "Supprimez-le explicitement avant un nouvel export."
        )


def export_partition(
    engine,
    name: str,
    where_clause: str,
    output_path: Path,
) -> None:
    """
    Exporte une partition PostgreSQL vers Parquet.

    L'écriture se fait d'abord dans un fichier temporaire.
    Le fichier final n'est créé qu'après validation complète.
    """

    validate_existing_target(output_path)

    temp_path = output_path.with_suffix(
        ".tmp.parquet"
    )

    # Nettoyage d'un éventuel résidu d'une exécution interrompue.
    if temp_path.exists():
        temp_path.unlink()

    query = text(
        f"""
        SELECT
            {SELECT_COLUMNS}
        FROM transactions_raw
        WHERE {where_clause}
        ORDER BY step
        """
    )

    expected = EXPECTED[name]

    writer = None
    rows_written = 0
    frauds_written = 0
    min_step_seen = None
    max_step_seen = None

    try:
        with engine.connect() as connection:

            chunks = pd.read_sql_query(
                query,
                connection,
                chunksize=CHUNK_SIZE,
            )

            for chunk_number, chunk in enumerate(
                chunks,
                start=1,
            ):
                if chunk.empty:
                    continue

                rows_written += len(chunk)
                frauds_written += int(
                    chunk["is_fraud"].sum()
                )

                chunk_min_step = int(
                    chunk["step"].min()
                )

                chunk_max_step = int(
                    chunk["step"].max()
                )

                if min_step_seen is None:
                    min_step_seen = chunk_min_step
                else:
                    min_step_seen = min(
                        min_step_seen,
                        chunk_min_step,
                    )

                if max_step_seen is None:
                    max_step_seen = chunk_max_step
                else:
                    max_step_seen = max(
                        max_step_seen,
                        chunk_max_step,
                    )

                table = pa.Table.from_pandas(
                    chunk,
                    preserve_index=False,
                )

                if writer is None:
                    writer = pq.ParquetWriter(
                        temp_path,
                        table.schema,
                        compression="snappy",
                    )

                writer.write_table(table)

                print(
                    f"{name:<10} | "
                    f"chunk {chunk_number:>2} | "
                    f"{rows_written:,} lignes"
                )

        if writer is None:
            raise RuntimeError(
                f"{name}: aucune donnée exportée."
            )

        writer.close()
        writer = None

        # ---------------------------------------------------------
        # Contrôles après écriture
        # ---------------------------------------------------------

        if not temp_path.exists():
            raise RuntimeError(
                f"{name}: fichier temporaire absent."
            )

        if temp_path.stat().st_size == 0:
            raise RuntimeError(
                f"{name}: fichier temporaire vide."
            )

        metadata = pq.ParquetFile(
            temp_path
        ).metadata

        parquet_rows = metadata.num_rows

        checks = {
            "rows": rows_written,
            "frauds": frauds_written,
            "min_step": min_step_seen,
            "max_step": max_step_seen,
        }

        print()
        print(f"Validation {name}")
        print("-" * 40)
        print(
            f"Lignes   : "
            f"{checks['rows']:,}"
        )
        print(
            f"Fraudes  : "
            f"{checks['frauds']:,}"
        )
        print(
            f"Steps    : "
            f"{checks['min_step']} "
            f"→ {checks['max_step']}"
        )
        print(
            f"Parquet  : "
            f"{parquet_rows:,} lignes"
        )
        print(
            f"Taille   : "
            f"{temp_path.stat().st_size:,} octets"
        )

        if rows_written != expected["rows"]:
            raise RuntimeError(
                f"{name}: nombre de lignes incorrect. "
                f"{rows_written:,} obtenu contre "
                f"{expected['rows']:,} attendu."
            )

        if parquet_rows != expected["rows"]:
            raise RuntimeError(
                f"{name}: métadonnées Parquet incorrectes."
            )

        if frauds_written != expected["frauds"]:
            raise RuntimeError(
                f"{name}: nombre de fraudes incorrect. "
                f"{frauds_written:,} obtenu contre "
                f"{expected['frauds']:,} attendu."
            )

        if min_step_seen != expected["min_step"]:
            raise RuntimeError(
                f"{name}: min_step incorrect."
            )

        if max_step_seen != expected["max_step"]:
            raise RuntimeError(
                f"{name}: max_step incorrect."
            )

        # ---------------------------------------------------------
        # Publication atomique
        # ---------------------------------------------------------

        os.replace(
            temp_path,
            output_path,
        )

        print(
            f"{name}: export validé → "
            f"{output_path}"
        )
        print()

    except Exception:

        if writer is not None:
            writer.close()

        if temp_path.exists():
            temp_path.unlink()

        raise


def main() -> None:
    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    train_path = (
        PROCESSED_DATA_DIR
        / "train.parquet"
    )

    validation_path = (
        PROCESSED_DATA_DIR
        / "validation.parquet"
    )

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        export_partition(
            engine=engine,
            name="train",
            where_clause=(
                f"step <= {TRAIN_END_STEP}"
            ),
            output_path=train_path,
        )

        export_partition(
            engine=engine,
            name="validation",
            where_clause=(
                f"step > {TRAIN_END_STEP} "
                f"AND step <= "
                f"{VALIDATION_END_STEP}"
            ),
            output_path=validation_path,
        )

    finally:
        engine.dispose()

    print("=" * 60)
    print("EXPORT TRAIN / VALIDATION TERMINÉ")
    print("=" * 60)
    print()
    print(f"Train      : {train_path}")
    print(
        f"Validation : {validation_path}"
    )
    print()
    print(
        "Le Test n'a volontairement "
        "pas été exporté."
    )


if __name__ == "__main__":
    main()