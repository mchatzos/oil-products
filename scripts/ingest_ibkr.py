#!/usr/bin/env python3
"""
Usage:
  python scripts/ingest_ibkr.py --product HO            # Heating Oil, 10Y
  python scripts/ingest_ibkr.py --product CL --years 5  # WTI, 5Y
  python scripts/ingest_ibkr.py                         # all products, 10Y
  python scripts/ingest_ibkr.py --port 7496             # TWS instead of Gateway
  python scripts/ingest_ibkr.py --query "SELECT * FROM futures_curves LIMIT 10"

Requires IB Gateway (port 4001) or TWS (port 7496) running locally.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from eia.db import Database
from ibkr import IBKRClient, IBKRIngestor, PRODUCTS


def main():
    parser = argparse.ArgumentParser(description="IBKR futures curve ingestion")
    parser.add_argument("--host",      default="127.0.0.1")
    parser.add_argument("--port",      type=int, default=4001, help="4001=Gateway, 7496=TWS")
    parser.add_argument("--client-id", type=int, default=1, dest="client_id")
    parser.add_argument("--product",   choices=list(PRODUCTS), default=None)
    parser.add_argument("--years",     type=int, default=10, help="Years of history to pull")
    parser.add_argument("--db",        default="oil_products.duckdb")
    parser.add_argument("--query",     default=None)
    args = parser.parse_args()

    with Database(args.db) as db:
        if args.query:
            print(db.query(args.query).to_string())
            return

        with IBKRClient(host=args.host, port=args.port, client_id=args.client_id) as client:
            ingestor = IBKRIngestor(client, db)
            if args.product:
                ingestor.ingest_product(args.product, years=args.years)
            else:
                ingestor.ingest_all(years=args.years)


if __name__ == "__main__":
    main()
