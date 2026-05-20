import time
from datetime import date, datetime
from typing import Optional

from .client import IBKRClient
from eia_oil.db import Database

# (exchange, currency) per product
# ICE Gasoil (QS) uses exchange 'IPE' in IBKR — verify in TWS if it resolves no contracts
PRODUCTS = {
    "CL": ("NYMEX", "USD"),  # WTI Crude Oil
    "BZ": ("NYMEX", "USD"),  # Brent Crude Oil
    "RB": ("NYMEX", "USD"),  # RBOB Gasoline
    "HO": ("NYMEX", "USD"),  # NY Harbor ULSD (Heating Oil)
    "QS": ("IPE",   "USD"),  # ICE Gasoil
}

# IBKR pacing: sustained rate of ~40 historical requests/min is safe
_REQUEST_DELAY = 1.5


class IBKRIngestor:
    def __init__(self, client: IBKRClient, db: Database):
        self.client = client
        self.db = db

    def ingest_product(self, symbol: str, exchange: str, currency: str, lookback: str = "2 Y"):
        details = self.client.get_contract_details(symbol, exchange, currency)
        print(f"{symbol}: {len(details)} contracts found")

        for cd in details:
            contract = cd.contract
            raw_expiry = contract.lastTradeDateOrContractMonth
            contract_month = raw_expiry[:6]  # YYYYMM

            try:
                bars = self.client.get_historical_bars(contract, duration=lookback)
                if not bars:
                    print(f"  {symbol} {contract_month}: no data")
                    continue

                records = []
                for bar in bars:
                    bar_date = bar.date if isinstance(bar.date, date) else bar.date.date()
                    records.append({
                        "trade_date": bar_date,
                        "root_symbol": symbol,
                        "exchange": exchange,
                        "contract_month": contract_month,
                        "expiry_date": _parse_expiry(raw_expiry),
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "wap": getattr(bar, "wap", None),
                        "bar_count": getattr(bar, "barCount", None),
                        "currency": currency,
                    })

                self.db.upsert("futures_curves", records, ["trade_date", "root_symbol", "contract_month"])
                print(f"  {symbol} {contract_month}: {len(records)} bars upserted")

            except Exception as exc:
                print(f"  {symbol} {contract_month}: error — {exc}")

            time.sleep(_REQUEST_DELAY)

    def ingest_all(self, lookback: str = "2 Y"):
        for symbol, (exchange, currency) in PRODUCTS.items():
            self.ingest_product(symbol, exchange, currency, lookback)

    def ingest_by_name(self, name: str, lookback: str = "2 Y"):
        if name not in PRODUCTS:
            raise ValueError(f"Unknown product '{name}'. Choose from: {list(PRODUCTS)}")
        exchange, currency = PRODUCTS[name]
        self.ingest_product(name, exchange, currency, lookback)


def _parse_expiry(val: str) -> Optional[date]:
    if len(val) >= 8:
        try:
            return datetime.strptime(val[:8], "%Y%m%d").date()
        except ValueError:
            pass
    if len(val) >= 6:
        try:
            return datetime.strptime(val[:6], "%Y%m").date()
        except ValueError:
            pass
    return None
