from datetime import date
from typing import Optional
from .client import EIAClient
from .db import Database


def _parse_date(val: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


class Ingestor:
    def __init__(self, client: EIAClient, db: Database):
        self.client = client
        self.db = db

    def ingest_crude_prices(self, start: str = "2000-01-01", end: Optional[str] = None):
        """WTI and Brent spot prices (weekly)."""
        params = {
            "data[]": "value",
            "facets[series][]": ["RWTC", "RBRTE"],  # WTI Cushing, Brent Europe
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "start": start,
        }
        if end:
            params["end"] = end

        rows = self.client.fetch("petroleum/pri/spt/data/", params)
        records = [
            {
                "period": _parse_date(r["period"]),
                "series_id": r["series"],
                "series_desc": r.get("series-description", ""),
                "value": r.get("value"),
                "units": r.get("units", "Dollars per Barrel"),
            }
            for r in rows
        ]
        self.db.upsert("crude_prices", records, ["period", "series_id"])
        print(f"crude_prices: {len(records)} rows upserted")

    def ingest_crude_production(self, start: str = "2000-01-01", end: Optional[str] = None):
        """U.S. monthly crude oil production by state/area."""
        params = {
            "data[]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "start": start,
        }
        if end:
            params["end"] = end

        rows = self.client.fetch("petroleum/crd/crpdn/data/", params)
        records = [
            {
                "period": _parse_date(r["period"]),
                "area_id": r.get("area-id", r.get("duoarea", "")),
                "area_name": r.get("area-name", r.get("areaName", "")),
                "value": r.get("value"),
                "units": r.get("units", "Thousand Barrels"),
            }
            for r in rows
        ]
        self.db.upsert("crude_production", records, ["period", "area_id"])
        print(f"crude_production: {len(records)} rows upserted")

    def ingest_crude_inventories(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Weekly U.S. crude oil inventories."""
        params = {
            "data[]": "value",
            "facets[series][]": ["WCRSTUS1"],  # U.S. ending stocks, crude oil
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "start": start,
        }
        if end:
            params["end"] = end

        rows = self.client.fetch("petroleum/stoc/wstk/data/", params)
        records = [
            {
                "period": _parse_date(r["period"]),
                "series_id": r["series"],
                "series_desc": r.get("series-description", ""),
                "value": r.get("value"),
                "units": r.get("units", "Thousand Barrels"),
            }
            for r in rows
        ]
        self.db.upsert("crude_inventories", records, ["period", "series_id"])
        print(f"crude_inventories: {len(records)} rows upserted")

    def ingest_all(self, start: str = "2000-01-01", end: Optional[str] = None):
        self.ingest_crude_prices(start, end)
        self.ingest_crude_production(start, end)
        self.ingest_crude_inventories(start, end)
