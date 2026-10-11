from __future__ import annotations

from datetime import date
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Hotel(Base):
    __tablename__ = "hotels"
    __table_args__ = (UniqueConstraint("code", name="uq_hotels_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="CO")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Bogota")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rooms: Mapped[list["Room"]] = relationship(back_populates="hotel", cascade="all, delete-orphan")
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="hotel", cascade="all, delete-orphan")
    rates: Mapped[list["Rate"]] = relationship(back_populates="hotel", cascade="all, delete-orphan")


class RoomType(Base):
    __tablename__ = "room_types"
    __table_args__ = (UniqueConstraint("code", name="uq_room_types_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    max_guests: Mapped[int] = mapped_column(Integer, nullable=False)

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="room_type")
    rates: Mapped[list["Rate"]] = relationship(back_populates="room_type")


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("hotel_id", "room_number", name="uq_rooms_hotel_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"), nullable=False)
    room_number: Mapped[str] = mapped_column(String(10), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    hotel: Mapped[Hotel] = relationship(back_populates="rooms")
    room_type: Mapped[RoomType] = relationship(back_populates="rooms")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("hotel_id", "room_type_id", "inventory_date", name="uq_inventory_hotel_type_date"),
        CheckConstraint("available_rooms >= 0", name="ck_inventory_available_nonnegative"),
        CheckConstraint("total_rooms >= available_rooms", name="ck_inventory_total_gte_available"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"), nullable=False)
    inventory_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    available_rooms: Mapped[int] = mapped_column(Integer, nullable=False)

    hotel: Mapped[Hotel] = relationship(back_populates="inventory")
    room_type: Mapped[RoomType] = relationship(back_populates="inventory")


class Rate(Base):
    __tablename__ = "rates"
    __table_args__ = (
        UniqueConstraint("hotel_id", "room_type_id", "season_code", name="uq_rates_hotel_type_season"),
        CheckConstraint("valid_to >= valid_from", name="ck_rates_valid_dates"),
        CheckConstraint("amount > 0", name="ck_rates_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"), nullable=False)
    season_code: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    hotel: Mapped[Hotel] = relationship(back_populates="rates")
    room_type: Mapped[RoomType] = relationship(back_populates="rates")
