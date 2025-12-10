# ==========================================================
# Export semantic views from DuckDB to CSV for Tableau
# - vw_production  -> data/vw_production.csv
# - vw_shipments   -> data/vw_shipments.csv
# - vw_finance     -> data/vw_finance.csv
# ==========================================================

import duckdb
import os

# Make sure data folder exists
os.makedirs("data", exist_ok=True)

# Connect to your DuckDB database file
con = duckdb.connect("duckdb/panpac.duckdb")

# List of views we want to export
views = ["vw_production", "vw_shipments", "vw_finance"]

for v in views:
    # Read the whole view into a DataFrame
    df = con.execute(f"SELECT * FROM {v}").fetchdf()

    # Build file path like data/vw_production.csv
    out_path = os.path.join("data", f"{v}.csv")

    # Save to CSV without index column
    df.to_csv(out_path, index=False)

    print(f"Exported {v} -> {out_path}")

print(">>> All semantic views exported for Tableau.")
