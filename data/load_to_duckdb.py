# ==========================================================
# Load Synthetic PanPac CSVs into DuckDB
# Database: ./duckdb/panpac.duckdb
# Plain English comments for easy understanding.
# ==========================================================

import duckdb
import os

# Connect to the DuckDB file
con = duckdb.connect("/Users/binhvo/panpac-bi-copilot/duckdb/panpac.duckdb")

# Path to your CSV data folder
DATA_PATH = "data"


# ----------------------------------------------------------
# Helper: load CSV into DuckDB with auto-detect schema
# ----------------------------------------------------------
def load_csv(table_name, file_name):
    """Loads a CSV file into DuckDB as a table with the same name."""
    file_path = os.path.join(DATA_PATH, file_name)
    con.execute(f"""
        CREATE TABLE {table_name} AS
        SELECT * FROM read_csv_auto('{file_path}', HEADER=TRUE);
    """)
    print(f"Loaded {table_name}")


# ----------------------------------------------------------
# Load Dimensions
# ----------------------------------------------------------
dim_tables = {
    "Dim_Date": "Dim_Date.csv",
    "Dim_Region": "Dim_Region.csv",
    "Dim_Site": "Dim_Site.csv",
    "Dim_Product": "Dim_Product.csv",
    "Dim_Customer": "Dim_Customer.csv"
}

for table, file in dim_tables.items():
    load_csv(table, file)


# ----------------------------------------------------------
# Load Fact Tables
# ----------------------------------------------------------
fact_tables = {
    "Fact_Production": "Fact_Production.csv",
    "Fact_Shipment": "Fact_Shipment.csv",
    "Fact_Finance": "Fact_Finance.csv"
}

for table, file in fact_tables.items():
    load_csv(table, file)

print(">>> All tables loaded into DuckDB!")
