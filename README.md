# eia-oil-ingest

Python tool for ingesting U.S. oil data from the [EIA API v2](https://www.eia.gov/opendata/) into a local DuckDB database.

## Datasets

| Table | Description | Frequency |
|---|---|---|
| `crude_prices` | WTI (Cushing) and Brent spot prices | Weekly |
| `crude_production` | U.S. crude oil production by state/area | Monthly |
| `crude_inventories` | U.S. crude oil ending stocks | Weekly |

## Setup

1. Get a free API key at <https://www.eia.gov/opendata/register.php>
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your key:
   ```bash
   cp .env.example .env
   # edit .env and set EIA_API_KEY=...
   ```

## Usage

```bash
# Ingest all datasets (default: from 2000-01-01)
python scripts/ingest.py

# Custom date range
python scripts/ingest.py --start 2020-01-01 --end 2024-12-31

# Single dataset
python scripts/ingest.py --dataset prices

# Query the database
python scripts/ingest.py --query "SELECT period, value FROM crude_prices WHERE series_id='RWTC' ORDER BY period DESC LIMIT 10"
```

## Storage

All data is stored in a single `eia_oil.duckdb` file (excluded from git). Years of oil data typically fit in under 50 MB.
