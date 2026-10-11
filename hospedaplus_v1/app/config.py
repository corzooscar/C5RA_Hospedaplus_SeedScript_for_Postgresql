from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://hospedaplus:hospedaplus_dev@localhost:5432/hospedaplus",
)
DEFAULT_SEED = int(os.getenv("SEED_RANDOM_SEED", "42"))
