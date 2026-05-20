import httpx
from typing import Any

BASE_URL = "https://api.eia.gov/v2"


class EIAClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.Client(timeout=30)

    def fetch(self, route: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Fetch all pages for a given EIA v2 route and return the merged data list."""
        params = dict(params or {})
        params["api_key"] = self.api_key
        params.setdefault("length", 5000)
        params.setdefault("offset", 0)

        rows: list[dict] = []
        while True:
            resp = self._client.get(f"{BASE_URL}/{route}", params=params)
            resp.raise_for_status()
            body = resp.json()["response"]
            page = body.get("data", [])
            rows.extend(page)
            total = body.get("total", len(rows))
            params["offset"] += len(page)
            if params["offset"] >= int(total) or not page:
                break

        return rows

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
