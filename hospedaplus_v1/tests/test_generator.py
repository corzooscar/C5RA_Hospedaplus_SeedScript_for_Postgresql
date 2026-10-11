from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from database.base import Base
from database.models import Hotel, Inventory, Rate, Room, RoomType
from seed.generator import seed_database


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def snapshot(session):
    result = {}
    for model in (Hotel, RoomType, Room, Inventory, Rate):
        rows = session.execute(select(model)).scalars().all()
        result[model.__tablename__] = [tuple(getattr(row, col.name) for col in model.__table__.columns) for row in rows]
    return result


def test_dev_seed_is_idempotent_and_reproducible():
    with make_session() as session:
        first_counts = seed_database(session, mode="dev", seed=123)
        first = snapshot(session)
        second_counts = seed_database(session, mode="dev", seed=123)
        second = snapshot(session)
        assert first_counts == second_counts
        assert first == second
        assert first_counts["hotels"] == 4
        assert first_counts["rooms"] == 120


def test_full_seed_volume():
    with make_session() as session:
        counts = seed_database(session, mode="full", seed=42)
        assert counts["hotels"] == 28
        assert session.scalar(select(func.count()).select_from(Room)) == 4000
