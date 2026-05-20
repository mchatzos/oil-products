"""
Build analysis-ready DataFrames from the local DuckDB database.
"""
import pandas as pd
import duckdb


UNIT_CAPACITY = {
    "CDU":      ("Atmospheric Crude Distillation Capacity",                             "B/CD"),
    "FCC":      ("Refinery Catalytic Cracking, Fresh Feed Downstream Charge Capacity",  "B/SD"),
    "HDC":      ("Catalytic Hydrocracking",                                             "B/SD"),
    "Coker":    ("Refinery Thermal Cracking/Delayed Coking Downstream Charge Capacity", "B/SD"),
    "Reformer": ("Catalytic Reforming",                                                 "B/SD"),
}

UNIT_THROUGHPUT = {
    "CDU":      "Crude Oil",
    "FCC":      "Downstream Catalytic Cracking",
    "HDC":      "Downstream Catalytic Hydrocracking",
    "Coker":    "Downstream Delayed Fluid Coking",
    "Reformer": "Catalytic Reforming Downstream Capacity",
}

PADDS = ["PADD 1", "PADD 2", "PADD 3", "PADD 4", "PADD 5"]


def refinery_unit_df(
    con: duckdb.DuckDBPyConnection,
    start: str = "2021-01-01",
    end: str | None = None,
) -> pd.DataFrame:
    """
    Return a multi-index DataFrame (month, unit, padd) with columns:
      capacity_kbd    — nameplate capacity, KBD (annual, forward-filled monthly)
      available_kbd   — capacity minus idle outage, KBD
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
            WHERE process_name = ? AND units = ?
              AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
              AND period >= ?
            ORDER BY period, area_name
        """, [process, units, start]).fetchdf()
        cap_df["period"] = pd.to_datetime(cap_df["period"])

        if unit == "CDU":
            idle_df = con.execute("""
                SELECT period, area_name, value AS idle_kbd
                FROM refinery_utilization
                WHERE process_name = 'Refinery Idle Operable Capacity'
                  AND units = 'MBBL/D'
                  AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
                  AND period >= ?
            """, [start]).fetchdf()
            idle_df["period"] = pd.to_datetime(idle_df["period"])
        else:
            idle_df = None

        if unit == "CDU":
            tput_df = con.execute("""
                SELECT DATE_TRUNC('month', period) AS period, area_name,
                       AVG(value) AS throughput_kbd
                FROM refinery_inputs
                WHERE product_name = 'Crude Oil' AND process_name = 'Refinery Net Input'
                  AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
                  AND period >= ?
                GROUP BY 1, 2
            """, [start]).fetchdf()
        else:
            tput_df = con.execute("""
                SELECT period, area_name, value AS throughput_kbd
                FROM unit_throughput
                WHERE process_name = ?
                  AND units = 'MBBL/D'
                  AND area_name IN ('PADD 1','PADD 2','PADD 3','PADD 4','PADD 5')
                  AND period >= ?
            """, [UNIT_THROUGHPUT[unit], start]).fetchdf()
        tput_df["period"] = pd.to_datetime(tput_df["period"])

        for padd in PADDS:
            cap_s = cap_df[cap_df.area_name == padd].set_index("period")["capacity_kbd"]
            cap_monthly = cap_s.reindex(months, method="ffill")

            if idle_df is not None:
                idle_s = idle_df[idle_df.area_name == padd].set_index("period")["idle_kbd"]
                idle_monthly = idle_s.reindex(months).fillna(0)
                avail_monthly = cap_monthly - idle_monthly
            else:
                avail_monthly = cap_monthly.copy()

            tput_s = tput_df[tput_df.area_name == padd].set_index("period")["throughput_kbd"]
            tput_monthly = tput_s.reindex(months)

            for month in months:
                records.append({
                    "month":          month,
                    "unit":           unit,
                    "padd":           padd,
                    "capacity_kbd":   round(cap_monthly.get(month, float("nan")), 1),
                    "available_kbd":  round(avail_monthly.get(month, float("nan")), 1),
                    "throughput_kbd": round(tput_monthly.get(month, float("nan")), 1),
                })

    return (
        pd.DataFrame(records)
        .set_index(["month", "unit", "padd"])
        .sort_index()
    )
