import time
from datetime import date, datetime
from typing import Optional

import pandas as pd

from .client import IBKRClient
from eia.db import Database

PRODUCTS = {
    "CL": ("NYMEX", "USD"),  # WTI Crude Oil
    "BZ": ("NYMEX", "USD"),  # Brent Crude Oil
    "RB": ("NYMEX", "USD"),  # RBOB Gasoline
    "HO": ("NYMEX", "USD"),  # NY Harbor ULSD (Heating Oil)
}

# IBKR pacing: safe sustained rate is ~40 historical requests / 10 min
_REQUEST_DELAY = 16.0  # seconds between requests (conservative for 10-year pull)


class IBKRIngestor:
    def __init__(self, client: IBKRClient, db: Database):
        self.client = client
        self.db = db

    def ingest_product(self, symbol: str, years: int = 10):
        exchange, currency = PRODUCTS[symbol]
        cutoff = (pd.Timestamp.today() - pd.DateOffset(years=years)).strftime("%Y%m")

        all_details = self.client.get_contracts(symbol, exchange, currency)
        details = [d for d in all_details if d.contract.lastTradeDateOrContractMonth[:6] >= cutoff]
        details.sort(key=lambda d: d.contract.lastTradeDateOrContractMonth)

        print(f"{symbol}: pulling {len(details)} contracts")

        today = pd.Timestamp.today()
        for cd in details:
            contract = cd.contract
            cm_str = contract.lastTradeDateOrContractMonth[:6]
            cm = pd.Timestamp(f"{cm_str[:4]}-{cm_str[4:6]}-01")
            end_dt = (cm + pd.offsets.MonthEnd(0)).strftime("%Y%m%d 23:59:59") if cm < today else ""

            try:
                bars = self.client.get_historical_bars(
                    contract=contract,
                    end_datetime=end_dt,
                    duration="2 Y",
                )

                if not bars:
                    print(f"  {symbol} {cm_str}: no data")
                    continue

                records = []
                for bar in bars:
                    bar_date = bar.date if isinstance(bar.date, date) else bar.date.date()
                    records.append({
                        "trade_date":     bar_date,
                        "root_symbol":    symbol,
                        "exchange":       exchange,
                        "contract_month": cm_str,
                        "expiry_date":    pd.Timestamp(cd.realExpirationDate or (cm + pd.offsets.MonthEnd(0))).date(),
                        "open":           bar.open,
                        "high":           bar.high,
                        "low":            bar.low,
                        "close":          bar.close,
                        "volume":         bar.volume,
                        "wap":            getattr(bar, "wap", None),
                        "bar_count":      getattr(bar, "barCount", None),
                        "currency":       currency,
                    })

                self.db.upsert("futures_curves", records, ["trade_date", "root_symbol", "contract_month"])
                print(f"  {symbol} {cm_str}: {len(records)} bars upserted")

            except Exception as exc:
                print(f"  {symbol} {cm_str}: error — {exc}")

            time.sleep(_REQUEST_DELAY)

    def ingest_all(self, years: int = 10):
        for symbol in PRODUCTS:
            self.ingest_product(symbol, years=years)
