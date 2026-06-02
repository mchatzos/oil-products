import duckdb
from pathlib import Path


class Database:
    def __init__(self, path: str = "oil_products.duckdb"):
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
        for table in (
            "product_stocks",
            "stocks_by_type",
            "stocks_by_state",
            "cushing_stocks",
            "refinery_utilization",
            "refinery_inputs",
            "refinery_production",
            "unit_throughput",
            "refinery_production_monthly",
        ):
            self._create_facet_table(table)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS futures_curves (
                trade_date      DATE        NOT NULL,
                root_symbol     VARCHAR     NOT NULL,
                exchange        VARCHAR     NOT NULL,
                contract_month  VARCHAR     NOT NULL,
                expiry_date     DATE,
                open            DOUBLE,
                high            DOUBLE,
                low             DOUBLE,
                close           DOUBLE,
                volume          BIGINT,
                wap             DOUBLE,
                bar_count       INTEGER,
                currency        VARCHAR,
                PRIMARY KEY (trade_date, root_symbol, contract_month)
            )
        """)

    def _create_facet_table(self, table: str):
        self.con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                period       DATE     NOT NULL,
                duoarea      VARCHAR  NOT NULL,
                area_name    VARCHAR,
                product      VARCHAR  NOT NULL,
                product_name VARCHAR,
                process      VARCHAR  NOT NULL,
                process_name VARCHAR,
                series       VARCHAR  NOT NULL,
                series_desc  VARCHAR,
                value        DOUBLE,
                units        VARCHAR,
                PRIMARY KEY (period, series)
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
