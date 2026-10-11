# HospedaPlus Revenue — Operational DB Seed (V1)

Initial, intentionally evolvable implementation for Jira story **US-23 / B0-86**. It creates a synthetic hotel catalog, physical rooms, dated inventory and seasonal rates in PostgreSQL.

## Scope of this version

- `dev`: 4 hotels, 120 rooms and 7 days of inventory.
- `full`: 28 hotels, 4,000 rooms and 30 days of inventory.
- A fixed random seed makes generated values reproducible.
- Re-running the seed replaces the generated catalog tables instead of appending duplicates.
- Room types, hotels, rooms, inventory and rates have foreign keys and uniqueness/check constraints.

> **Important:** this V1 treats the seed-owned tables as generated data and deletes their contents before repopulating them. Use a dedicated development/test database. Do not run against manually maintained operational data.

## Requirements

- Python 3.11+
- Docker Desktop (or Docker Engine) with Docker Compose

## Run locally

```bash
# 1. Create environment and install dependencies (Windows PowerShell)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"

# 2. Configure environment
Copy-Item .env.example .env

# 3. Start PostgreSQL
 docker compose up -d postgres

# 4. Generate the small development dataset
python -m seed.run --mode dev --seed 42

# 5. Generate the complete dataset
python -m seed.run --mode full --seed 42

# 6. Run tests
pytest
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy `.env.example` to `.env` using `cp`.

## Current conceptual model

- `hotels`: hotel catalog and timezone.
- `room_types`: room-type catalog and guest capacity.
- `rooms`: physical rooms assigned to a hotel and room type.
- `inventory`: available and total rooms by hotel, room type and date.
- `rates`: seasonal rates with validity dates and currency.

Physical rooms are distinct from dated commercial inventory. This avoids treating the physical room count as the available inventory for every date.

## Known V1 limitations / next iteration

1. Schema creation currently uses `Base.metadata.create_all()` as a bootstrap convenience. Add an initial Alembic migration before treating schema changes as versioned project workflow.
2. Inventory dates currently start on `2026-01-01`; make the horizon configurable in a follow-up.
3. Seasonal validity windows currently share the same full-year validity range; define actual season windows with the business team.
4. The five known quality defects in the project specification are not injected by this seed yet. Add a configurable defect-rate layer once the event/reservation and agency-file data contracts are finalized; do not inject defects into core hotel/room catalogs.
5. The first implementation is a catalog/inventory/rates seed. Direct reservations and channel-specific event entities should be added after aligning with the event simulator US-24 and the data-quality catalog US-14.
6. The current `dev` and `full` volumes are fixed presets; make room counts and date horizon independently configurable if required.

## Design principle

This is a first schema, not a claim that the final data model is settled. Add changes through model updates and migrations, and keep generation rules in `seed/` rather than embedding them in API code.
