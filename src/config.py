import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")


# ---------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------

RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"

PAYSIM_CSV = RAW_DATA_DIR / "PS_20174392719_1491204439457_log.csv"


# ---------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "fraud")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))


DB_CONFIG = {
    "host": POSTGRES_HOST,
    "port": POSTGRES_PORT,
    "dbname": POSTGRES_DB,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}


DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# ---------------------------------------------------------------------
# Protocole temporel — GELÉ
# ---------------------------------------------------------------------

SPLIT_VERSION = "temporal_volume_70_15_15_v1"

TRAIN_END_STEP = 323
VALIDATION_END_STEP = 377

TARGET_COLUMN = "is_fraud"

# Colonnes brutes admissibles pour construire le jeu de modélisation.
# Les identifiants sont conservés uniquement pour permettre de futures
# features historiques ; ils ne seront pas injectés directement dans
# les modèles.
MODELING_COLUMNS = (
    "step",
    "type",
    "amount",
    "name_orig",
    "oldbalance_org",
    "name_dest",
    "oldbalance_dest",
    "is_fraud",
)