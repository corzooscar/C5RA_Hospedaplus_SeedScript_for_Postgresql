"""
US-26 (B0-97/B0-98/B0-99) - Unified, configurable data-quality defect rates.

This module is the single source of truth for the injection rate of each of
the 5 defects catalogued in US-14 (data_quality_defects_catalog.md), so that
F2 (channel-manager events, US-24), F3 (this seed, US-23) and F4 (agency
files, US-25) all read their defaults from the same place instead of each
picking their own number.

Defaults are deliberately low: section 5.3 frames these as anomalies that a
downstream data-quality check must be able to catch, not the common case.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefectRates:
    # Defect 1 - reservations with adults = children = infants = 0 (F3).
    zero_guests_rate: float = 0.02
    # Defect 2 - check_out < check_in (F3; F2 already supports this via its
    # own out-of-order mechanism, see event_generator.py).
    invalid_date_range_rate: float = 0.02
    # Defect 3 - currency left blank in agency files (F4). Replaces the
    # previously hardcoded ~33% (rng.choice(["EUR", "USD", None])).
    missing_currency_rate: float = 0.10
    # Defect 4 - duplicate reservation across channels with a varied guest
    # name (F4 vs F2). Exposed as a rate for documentation consistency with
    # the other four defects; agency_files.py still takes an absolute count
    # as its primary parameter (see README "Defect 4" note for why).
    duplicate_rate: float = 0.10
    # Defect 5 - a modification event delivered before its creation event
    # (F2). Already fully implemented in US-24 as --out-of-order-rate.
    out_of_order_rate: float = 0.10

    def __post_init__(self) -> None:
        for name in ("zero_guests_rate", "invalid_date_range_rate",
                      "missing_currency_rate", "duplicate_rate", "out_of_order_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


DEFAULT_DEFECT_RATES = DefectRates()
