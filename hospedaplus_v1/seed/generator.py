from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.models import DirectBooking, Hotel, Inventory, Rate, Room, RoomType
from seed.defects import DEFAULT_DEFECT_RATES, DefectRates

ROOM_TYPES = [
    ("SINGLE", "Single", 1),
    ("DOUBLE", "Double", 2),
    ("FAMILY", "Family", 4),
    ("SUITE", "Suite", 3),
]
CITIES = ["Barranquilla", "Cartagena", "Santa Marta", "Bogota", "Medellin", "Cali", "Bucaramanga"]
SEASONS = [("LOW", 1.0), ("SHOULDER", 1.25), ("HIGH", 1.6)]

# Defect 1/2 are only ever injected into direct_bookings, never into the
# catalog tables above (US-23 limitation #4). bookings_per_hotel is modest by
# design: this table exists to demonstrate the two defects, not to model full
# reservation volume (that remains F1/F2/F4's job).
BOOKINGS_PER_HOTEL = {"dev": 15, "full": 60}


def seed_database(
    session: Session,
    mode: str = "dev",
    seed: int = 42,
    defect_rates: DefectRates = DEFAULT_DEFECT_RATES,
) -> dict[str, int]:
    """Replace generated seed data deterministically; safe to run repeatedly.

    This V1 intentionally owns the generated catalog tables. Do not point it at
    a database containing hand-maintained data until this ownership contract is reviewed.

    `defect_rates` controls the configurable injection of US-14's defects 1
    (zero guests) and 2 (check-out before check-in) into direct_bookings
    only - see seed/defects.py and US-26 (B0-97).
    """
    if mode not in {"dev", "full"}:
        raise ValueError("mode must be 'dev' or 'full'")

    rng = random.Random(seed)
    hotel_count = 4 if mode == "dev" else 28
    room_target = 120 if mode == "dev" else 4000

    # Delete in dependency order so repeated runs produce the same generated state.
    session.execute(delete(DirectBooking))
    session.execute(delete(Inventory))
    session.execute(delete(Rate))
    session.execute(delete(Room))
    session.execute(delete(Hotel))
    session.execute(delete(RoomType))
    session.flush()

    room_types: dict[str, RoomType] = {}
    for code, name, max_guests in ROOM_TYPES:
        obj = RoomType(code=code, name=name, max_guests=max_guests)
        session.add(obj)
        room_types[code] = obj
    session.flush()

    hotels: list[Hotel] = []
    for i in range(hotel_count):
        city = CITIES[i % len(CITIES)]
        hotel = Hotel(
            code=f"HTL-{i + 1:03d}",
            name=f"HospedaPlus {city} {i // len(CITIES) + 1}",
            city=city,
            country="CO",
            timezone="America/Bogota",
            is_active=True,
        )
        session.add(hotel)
        hotels.append(hotel)
    session.flush()

    base_rooms, remainder = divmod(room_target, hotel_count)
    room_counts: dict[tuple[int, str], int] = {}
    for index, hotel in enumerate(hotels):
        count = base_rooms + (1 if index < remainder else 0)
        per_type = [count // len(ROOM_TYPES)] * len(ROOM_TYPES)
        for j in range(count % len(ROOM_TYPES)):
            per_type[j] += 1
        room_number = 1
        for (type_code, _, _), type_count in zip(ROOM_TYPES, per_type):
            room_counts[(hotel.id, type_code)] = type_count
            for _ in range(type_count):
                session.add(Room(
                    hotel_id=hotel.id,
                    room_type_id=room_types[type_code].id,
                    room_number=f"{room_number:03d}",
                    floor=((room_number - 1) // 25) + 1,
                    is_active=True,
                ))
                room_number += 1

    start_date = date(2026, 1, 1)
    days = 7 if mode == "dev" else 30
    for hotel in hotels:
        for type_code, _, _ in ROOM_TYPES:
            total = room_counts[(hotel.id, type_code)]
            for day_offset in range(days):
                current_date = start_date + timedelta(days=day_offset)
                # Synthetic occupancy changes with the seeded RNG but remains reproducible.
                occupancy = rng.uniform(0.25, 0.85)
                available = max(0, min(total, round(total * (1 - occupancy))))
                session.add(Inventory(
                    hotel_id=hotel.id,
                    room_type_id=room_types[type_code].id,
                    inventory_date=current_date,
                    total_rooms=total,
                    available_rooms=available,
                ))
            for season_code, multiplier in SEASONS:
                base_rate = {"SINGLE": 120000, "DOUBLE": 180000, "FAMILY": 260000, "SUITE": 350000}[type_code]
                # Integer-valued COP prices keep the generated data predictable and readable.
                amount = Decimal(round(base_rate * multiplier * rng.uniform(0.9, 1.1), -3))
                session.add(Rate(
                    hotel_id=hotel.id,
                    room_type_id=room_types[type_code].id,
                    season_code=season_code,
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2026, 12, 31),
                    currency="COP",
                    amount=amount,
                ))

    # --- direct_bookings (F3 reservations) + defects 1 and 2 (US-26) ---
    bookings_per_hotel = BOOKINGS_PER_HOTEL[mode]
    zero_guests_injected = 0
    invalid_date_range_injected = 0
    booking_counter = 0
    room_type_codes = [code for code, _, _ in ROOM_TYPES]

    for hotel in hotels:
        for _ in range(bookings_per_hotel):
            booking_counter += 1
            type_code = rng.choice(room_type_codes)
            stay_nights = rng.randint(1, 7)
            check_in = start_date + timedelta(days=rng.randint(0, 300))
            check_out = check_in + timedelta(days=stay_nights)
            adults = rng.randint(1, 3)
            children = rng.randint(0, 2)
            infants = 0

            has_zero_guests = rng.random() < defect_rates.zero_guests_rate
            if has_zero_guests:
                adults = children = infants = 0
                zero_guests_injected += 1

            has_invalid_range = rng.random() < defect_rates.invalid_date_range_rate
            if has_invalid_range:
                # Swap so check_out ends up strictly before check_in, instead
                # of just shortening the stay - this must be unambiguously
                # invalid, not merely a 0-night edge case.
                check_in, check_out = check_out, check_in
                invalid_date_range_injected += 1

            base_rate = {"SINGLE": 120000, "DOUBLE": 180000, "FAMILY": 260000, "SUITE": 350000}[type_code]
            total_amount = Decimal(round(base_rate * max(stay_nights, 1) * rng.uniform(0.9, 1.1), -3))

            session.add(DirectBooking(
                booking_code=f"DB-{hotel.code}-{booking_counter:05d}",
                hotel_id=hotel.id,
                room_type_id=room_types[type_code].id,
                check_in=check_in,
                check_out=check_out,
                adults=adults,
                children=children,
                infants=infants,
                currency="COP",
                total_amount=total_amount,
                created_at=datetime(2026, 1, 1) + timedelta(days=rng.randint(0, 300)),
                has_zero_guests_defect=has_zero_guests,
                has_invalid_date_range_defect=has_invalid_range,
            ))

    direct_booking_rows = hotel_count * bookings_per_hotel

    session.commit()
    return {
        "hotels": hotel_count,
        "rooms": room_target,
        "room_types": len(ROOM_TYPES),
        "inventory_rows": hotel_count * len(ROOM_TYPES) * days,
        "rate_rows": hotel_count * len(ROOM_TYPES) * len(SEASONS),
        "direct_booking_rows": direct_booking_rows,
        "zero_guests_defects": zero_guests_injected,
        "invalid_date_range_defects": invalid_date_range_injected,
    }
