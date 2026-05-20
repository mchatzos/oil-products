#!/usr/bin/env python3
"""
Usage:
  python scripts/ingest_ibkr.py                          # all products, 2Y lookback
  python scripts/ingest_ibkr.py --product CL             # WTI only
  python scripts/ingest_ibkr.py --product RB --lookback "1 Y"
  python scripts/ingest_ibkr.py --port 7496              # TWS instead of Gateway
  python scripts/ingest_ibkr.py --query "SELECT root_symbol, contract_month, close FROM futures_curves LIMIT 20"

Requires IB Gateway (port 4001) or TWS (port 7496) running locally.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from eia_oil.db import Database
from ibkr import IBKRClient, IBKRIngestor, PRODUCTS


def main():
    parser = argparse.ArgumentParser(description="IBKR futures curve ingestion")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4001, help="4001=Gateway, 7496=TWS")
    parser.add_argument("--client-id", type=int, default=1, dest="client_id")
    parser.add_argument(
        "--product",
        choices=list(PRODUCTS),
        default=None,
        help="Single product to ingest (default: all)",
    )
    parser.add_argument(
        "--lookback",
        default="2 Y",
        help='IBKR duration string, e.g. "2 Y", "6 M" (default: "2 Y")',
    )
    parser.add_argument("--db", default="eia_oil.duckdb", help="DuckDB file path")
    parser.add_argument("--query", default=None, help="Run a SQL query and print results")
    args = parser.parse_args()

    with Database(args.db) as db:
        if args.query:
            print(db.query(args.query).to_string())
            return

        with IBKRClient(host=args.host, port=args.port, client_id=args.client_id) as client:
            ingestor = IBKRIngestor(client, db)
            if args.product:
                ingestor.ingest_by_name(args.product, lookback=args.lookback)
            else:
                ingestor.ingest_all(lookback=args.lookback)


if __name__ == "__main__":
    main()
