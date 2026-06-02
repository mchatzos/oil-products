"""
Build analysis-ready DataFrames from the local DuckDB database.
"""
from typing import Optional
import pandas as pd
import duckdb


UNIT_CAPACITY = {
    "CDU":      ("Atmospheric Crude Distillation Capacity",                             "B/CD"),
    "FCC":      ("Refinery Catalytic Cracking, Fresh Feed Downstream Charge Capacity",  "B/SD"),
    "HDC":      ("Catalytic Hydrocracking",                                             "B/SD"),
    "Coker":    ("Refinery Thermal Cracking/Delayed Coking Downstream Charge Capacity", "B/SD"),
    "Reformer": ("Catalytic Reforming",                                                 "B/SD"),
}

# (table, filter_column, filter_value, weekly_avg)
# weekly_avg=True → DATE_TRUNC + AVG; False → direct select
UNIT_THROUGHPUT_SOURCE = {
    "CDU":      ("refinery_inputs",  "product_name", "Crude Oil",                           True),
    "FCC":      ("unit_throughput",  "process_name", "Downstream Catalytic Cracking",        False),
    "HDC":      ("unit_throughput",  "process_name", "Downstream Catalytic Hydrocracking",   False),
    "Coker":    ("unit_throughput",  "process_name", "Downstream Delayed Fluid Coking",       False),
    "Reformer": ("unit_throughput",  "process_name", "Catalytic Reforming Downstream Capacity", False),
}

PADDS = ["PADD 1", "PADD 2", "PADD 3", "PADD 4", "PADD 5"]


def _query_throughput(
    con: duckdb.DuckDBPyConnection,
    table: str,
    filter_col: str,
    filter_val: str,
    weekly_avg: bool,
    start: str,
) -> pd.DataFrame:
    if weekly_avg:
        df = con.execute(f"""
            SELECT DATE_TRUNC('month', period) AS period, area_name,
                   AVG(value) AS throughput_kbd
            FROM {table}
            WHERE {filter_col} = ?
              AND process_name = 'Refinery Net Input'
              AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
              AND period >= ?
            GROUP BY 1, 2
        """, [filter_val, start]).fetchdf()
    else:
        df = con.execute(f"""
            SELECT period, area_name, value AS throughput_kbd
            FROM {table}
            WHERE {filter_col} = ?
              AND units = 'MBBL/D'
              AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
              AND period >= ?
        """, [filter_val, start]).fetchdf()
    df["period"] = pd.to_datetime(df["period"])
    return df


def refinery_unit_df(
    con: duckdb.DuckDBPyConnection,
    start: str = "2021-01-01",
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return a multi-index DataFrame (month, unit, padd) with columns:
      capacity_kbd    — nameplate capacity, KBD (annual survey, forward-filled monthly)
      available_kbd   — NaN for all units; EIA does not publish unit-level outage data
      throughput_kbd  — actual unit throughput, KBD (monthly)

    Units: CDU, FCC, HDC, Coker, Reformer
    PADDs: 1–5
    """
    end_ts = pd.Timestamp(end) if end else pd.Timestamp.today().replace(day=1)
    months = pd.date_range(start, end_ts, freq="MS")

    records = []

    for unit, (process, units) in UNIT_CAPACITY.items():
        cap_df = con.execute("""
            SELECT period, area_name, value / 1000.0 AS capacity_kbd
            FROM refinery_utilization
            WHERE TRIM(process_name) = TRIM(?) AND units = ?
              AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
              AND period >= ?
            ORDER BY period, area_name
        """, [process, units, start]).fetchdf()
        cap_df["period"] = pd.to_datetime(cap_df["period"])

        table, filter_col, filter_val, weekly_avg = UNIT_THROUGHPUT_SOURCE[unit]
        tput_df = _query_throughput(con, table, filter_col, filter_val, weekly_avg, start)

        for padd in PADDS:
            cap_monthly  = cap_df[cap_df.area_name == padd].set_index("period")["capacity_kbd"].reindex(months, method="ffill")
            tput_monthly = tput_df[tput_df.area_name == padd].set_index("period")["throughput_kbd"].reindex(months)

            for month, cap, tput in zip(months, cap_monthly.values, tput_monthly.values):
                records.append({
                    "month":          month,
                    "unit":           unit,
                    "padd":           padd,
                    "capacity_kbd":   round(float(cap), 1),
                    "available_kbd":  float("nan"),
                    "throughput_kbd": round(float(tput), 1),
                })

    return (
        pd.DataFrame(records)
        .set_index(["month", "unit", "padd"])
        .sort_index()
    )
