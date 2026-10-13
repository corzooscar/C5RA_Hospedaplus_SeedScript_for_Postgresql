from __future__ import annotations

import argparse

from app.config import DEFAULT_SEED
from database.connection import SessionLocal
from database.base import Base
from database import models  # noqa: F401 - registers mapped tables
from database.connection import engine
from seed.defects import DEFAULT_DEFECT_RATES, DefectRates
from seed.generator import seed_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate HospedaPlus synthetic operational data")
    parser.add_argument("--mode", choices=["dev", "full"], default="dev")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--zero-guests-rate", type=float, default=DEFAULT_DEFECT_RATES.zero_guests_rate,
                         help="US-26 defect 1: fraction of direct_bookings forced to adults=children=infants=0")
    parser.add_argument("--invalid-date-range-rate", type=float, default=DEFAULT_DEFECT_RATES.invalid_date_range_rate,
                         help="US-26 defect 2: fraction of direct_bookings with check_out before check_in")
    args = parser.parse_args()

    defect_rates = DefectRates(
        zero_guests_rate=args.zero_guests_rate,
        invalid_date_range_rate=args.invalid_date_range_rate,
    )

    # Temporary convenience for V1 bootstrap. Use Alembic migrations as the
    # canonical schema lifecycle once the initial migration is in place.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        counts = seed_database(session, mode=args.mode, seed=args.seed, defect_rates=defect_rates)
    print(f"Seed completed (mode={args.mode}, seed={args.seed}):")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
