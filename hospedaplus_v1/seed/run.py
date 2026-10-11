from __future__ import annotations

import argparse

from app.config import DEFAULT_SEED
from database.connection import SessionLocal
from database.base import Base
from database import models  # noqa: F401 - registers mapped tables
from database.connection import engine
from seed.generator import seed_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate HospedaPlus synthetic operational data")
    parser.add_argument("--mode", choices=["dev", "full"], default="dev")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    # Temporary convenience for V1 bootstrap. Use Alembic migrations as the
    # canonical schema lifecycle once the initial migration is in place.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        counts = seed_database(session, mode=args.mode, seed=args.seed)
    print(f"Seed completed (mode={args.mode}, seed={args.seed}):")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
