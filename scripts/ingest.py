#!/usr/bin/env python3
"""
Usage:
  python scripts/ingest.py                        # ingest all datasets from 2000
  python scripts/ingest.py --start 2020-01-01     # custom start date
  python scripts/ingest.py --dataset prices       # one dataset only
  python scripts/ingest.py --query "SELECT * FROM crude_prices LIMIT 10"
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from eia_oil import EIAClient, Database, Ingestor

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="EIA oil data ingestion")
    parser.add_argument("--start", default="2000-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--dataset",
        choices=[
            "prices", "production", "inventories",
            "product_stocks", "stocks_by_type", "stocks_by_state", "cushing_stocks",
            "refinery_utilization", "refinery_inputs", "refinery_production",
            "unit_throughput",
            "all",
        ],
        default="all",
    )
    parser.add_argument("--db", default="eia_oil.duckdb", help="DuckDB file path")
    parser.add_argument("--query", default=None, help="Run a SQL query and print results")
    args = parser.parse_args()

    api_key = os.getenv("EIA_API_KEY")
    if not api_key:
        sys.exit("Error: EIA_API_KEY not set. Copy .env.example to .env and add your key.")

    with EIAClient(api_key) as client, Database(args.db) as db:
        if args.query:
            print(db.query(args.query).to_string())
            return

        ingestor = Ingestor(client, db)
        dispatch = {
            "prices": ingestor.ingest_crude_prices,
            "production": ingestor.ingest_crude_production,
            "inventories": ingestor.ingest_crude_inventories,
            "product_stocks": ingestor.ingest_product_stocks,
            "stocks_by_type": ingestor.ingest_stocks_by_type,
            "stocks_by_state": ingestor.ingest_stocks_by_state,
            "cushing_stocks": ingestor.ingest_cushing_stocks,
            "refinery_utilization": ingestor.ingest_refinery_utilization,
            "refinery_inputs": ingestor.ingest_refinery_inputs,
            "refinery_production": ingestor.ingest_refinery_production,
            "unit_throughput": ingestor.ingest_unit_throughput,
            "all": lambda s, e: ingestor.ingest_all(s, e),
        }
        dispatch[args.dataset](args.start, args.end)


if __name__ == "__main__":
    main()
