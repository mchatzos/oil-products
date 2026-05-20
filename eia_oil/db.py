import duckdb
from pathlib import Path


class Database:
    def __init__(self, path: str = "eia_oil.duckdb"):
        self.path = Path(path)
        self.con = duckdb.connect(str(self.path))
        self._init_schema()

    def _init_schema(self):
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS crude_prices (
                period      DATE        NOT NULL,
                series_id   VARCHAR     NOT NULL,
                series_desc VARCHAR,
                value       DOUBLE,
                units       VARCHAR,
                PRIMARY KEY (period, series_id)
            )
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS crude_production (
                period      DATE        NOT NULL,
                area_id     VARCHAR     NOT NULL,
                area_name   VARCHAR,
                value       DOUBLE,
                units       VARCHAR,
                PRIMARY KEY (period, area_id)
            )
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS crude_inventories (
                period      DATE        NOT NULL,
                series_id   VARCHAR     NOT NULL,
                series_desc VARCHAR,
                value       DOUBLE,
                units       VARCHAR,
                PRIMARY KEY (period, series_id)
            )
        """)

    def upsert(self, table: str, rows: list[dict], key_cols: list[str]):
        if not rows:
            return
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_list = ", ".join(cols)
        conflict_cols = ", ".join(key_cols)
        update_set = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in cols if c not in key_cols
        )
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}"
        )
        self.con.executemany(sql, [list(r.values()) for r in rows])

    def query(self, sql: str):
        return self.con.execute(sql).fetchdf()

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
