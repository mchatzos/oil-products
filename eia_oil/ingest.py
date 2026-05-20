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

    def _fetch_facet_series(self, route: str, table: str, start: str, end: Optional[str]):
        """Generic fetch for routes that share the duoarea/product/process/series schema."""
        params = {
            "data[]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "start": start,
        }
        if end:
            params["end"] = end

        rows = self.client.fetch(route, params)
        records = [
            {
                "period": _parse_date(r["period"]),
                "duoarea": r.get("duoarea", ""),
                "area_name": r.get("area-name", ""),
                "product": r.get("product", ""),
                "product_name": r.get("product-name", ""),
                "process": r.get("process", ""),
                "process_name": r.get("process-name", ""),
                "series": r.get("series", ""),
                "series_desc": r.get("series-description", ""),
                "value": r.get("value"),
                "units": r.get("units", ""),
            }
            for r in rows
        ]
        self.db.upsert(table, records, ["period", "series"])
        print(f"{table}: {len(records)} rows upserted")

    def ingest_product_stocks(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Motor gasoline, distillate, propane ending stocks (monthly)."""
        self._fetch_facet_series("petroleum/stoc/ts/data/", "product_stocks", start, end)

    def ingest_stocks_by_type(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Petroleum stocks by type at bulk terminals, refineries, etc. (monthly)."""
        self._fetch_facet_series("petroleum/stoc/typ/data/", "stocks_by_type", start, end)

    def ingest_stocks_by_state(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Refinery, bulk terminal, and natural gas plant stocks by state (monthly)."""
        self._fetch_facet_series("petroleum/stoc/st/data/", "stocks_by_state", start, end)

    def ingest_cushing_stocks(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Crude oil stocks at Cushing and other tank farms & pipelines (monthly)."""
        self._fetch_facet_series("petroleum/stoc/cu/data/", "cushing_stocks", start, end)

    def ingest_refinery_utilization(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Refinery utilization and capacity (monthly + annual)."""
        self._fetch_facet_series("petroleum/pnp/unc/data/", "refinery_utilization", start, end)
        self._fetch_facet_series("petroleum/pnp/cap1/data/", "refinery_utilization", start, end)

    def ingest_refinery_inputs(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Weekly refinery and blender net inputs and utilization."""
        self._fetch_facet_series("petroleum/pnp/wiup/data/", "refinery_inputs", start, end)

    def ingest_refinery_production(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Weekly refinery and blender net production by product."""
        self._fetch_facet_series("petroleum/pnp/wprodrb/data/", "refinery_production", start, end)

    def ingest_unit_throughput(self, start: str = "2000-01-01", end: Optional[str] = None):
        """Monthly downstream unit throughput: FCC, HDC, coker, reformer by PADD."""
        self._fetch_facet_series("petroleum/pnp/dwns/data/", "unit_throughput", start, end)

    def ingest_all(self, start: str = "2000-01-01", end: Optional[str] = None):
        self.ingest_crude_prices(start, end)
        self.ingest_crude_production(start, end)
        self.ingest_crude_inventories(start, end)
        self.ingest_product_stocks(start, end)
        self.ingest_stocks_by_type(start, end)
        self.ingest_stocks_by_state(start, end)
        self.ingest_cushing_stocks(start, end)
        self.ingest_refinery_utilization(start, end)
        self.ingest_refinery_inputs(start, end)
        self.ingest_refinery_production(start, end)
        self.ingest_unit_throughput(start, end)
