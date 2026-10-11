from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.models import Hotel, Inventory, Rate, Room, RoomType

ROOM_TYPES = [
    ("SINGLE", "Single", 1),
    ("DOUBLE", "Double", 2),
    ("FAMILY", "Family", 4),
    ("SUITE", "Suite", 3),
]
CITIES = ["Barranquilla", "Cartagena", "Santa Marta", "Bogota", "Medellin", "Cali", "Bucaramanga"]
SEASONS = [("LOW", 1.0), ("SHOULDER", 1.25), ("HIGH", 1.6)]


def seed_database(session: Session, mode: str = "dev", seed: int = 42) -> dict[str, int]:
    """Replace generated seed data deterministically; safe to run repeatedly.

    This V1 intentionally owns the generated catalog tables. Do not point it at
    a database containing hand-maintained data until this ownership contract is reviewed.
    """
    if mode not in {"dev", "full"}:
        raise ValueError("mode must be 'dev' or 'full'")

    rng = random.Random(seed)
    hotel_count = 4 if mode == "dev" else 28
    room_target = 120 if mode == "dev" else 4000

    # Delete in dependency order so repeated runs produce the same generated state.
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

    session.commit()
    return {
        "hotels": hotel_count,
        "rooms": room_target,
        "room_types": len(ROOM_TYPES),
        "inventory_rows": hotel_count * len(ROOM_TYPES) * days,
        "rate_rows": hotel_count * len(ROOM_TYPES) * len(SEASONS),
    }
