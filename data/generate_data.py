# ===============================================================
# PanPac Synthetic Dataset Generator
# Generates: Dim_Date, Dim_Site, Dim_Product,
#            Dim_Region, Dim_Customer,
#            Fact_Production, Fact_Shipment, Fact_Finance
#
# Plain English comments for easy learning.
# Output saved to: ./data/*.csv
# ===============================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Ensure the /data folder exists
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------------
# 1. Generate Dim_Date
# ---------------------------------------------------------------

def generate_dim_date(start_date="2024-01-01", end_date="2025-12-31"):
    """Creates a full date dimension table for 2 years."""
    dates = pd.date_range(start=start_date, end=end_date)

    df = pd.DataFrame({
        "date_key": dates.strftime("%Y%m%d").astype(int),
        "date": dates,
        "day": dates.day,
        "month": dates.month,
        "month_name": dates.strftime("%B"),
        "quarter": dates.quarter,
        "year": dates.year,
        "weekday": dates.strftime("%A"),
        "is_weekend": dates.weekday >= 5
    })
    return df


# ---------------------------------------------------------------
# 2. Generate Dim_Region
# ---------------------------------------------------------------

def generate_dim_region():
    """Forestry/Export regions normally used by PanPac-like business."""
    regions = [
        (1, "Northland", "New Zealand"),
        (2, "Hawke's Bay", "New Zealand"),
        (3, "Waikato", "New Zealand"),
        (4, "Vietnam", "Export"),
        (5, "China", "Export"),
        (6, "Japan", "Export")
    ]

    df = pd.DataFrame(regions, columns=["region_key", "region_name", "country"])
    return df


# ---------------------------------------------------------------
# 3. Generate Dim_Site (Forests, Mills, Ports)
# ---------------------------------------------------------------

def generate_dim_site():
    """Basic site dimension with forests, mills and ports."""
    sites = [
        (1, "Forest A", "Forest", 1, 800),
        (2, "Forest B", "Forest", 2, 900),
        (3, "Mill A", "Mill", 2, 600),
        (4, "Mill B", "Mill", 3, 700),
        (5, "Napier Port", "Port", 2, 1200),
        (6, "Auckland Port", "Port", 1, 1500)
    ]

    df = pd.DataFrame(sites, columns=[
        "site_key", "site_name", "site_type", "region_key", "capacity_m3"
    ])
    return df


# ---------------------------------------------------------------
# 4. Generate Dim_Product
# ---------------------------------------------------------------

def generate_dim_product():
    """Forestry products (logs / timber / pulp)."""
    products = [
        (1, "Log A28", "Log", "A28", "m3"),
        (2, "Log B22", "Log", "B22", "m3"),
        (3, "Timber Premium", "Timber", "TP", "m3"),
        (4, "Timber Standard", "Timber", "TS", "m3"),
        (5, "Pulp High Grade", "Pulp", "PG", "tonne"),
        (6, "Pulp Low Grade", "Pulp", "PL", "tonne")
    ]

    df = pd.DataFrame(products, columns=[
        "product_key", "product_name", "product_type", "grade", "unit_of_measure"
    ])
    return df


# ---------------------------------------------------------------
# 5. Generate Dim_Customer
# ---------------------------------------------------------------

def generate_dim_customer():
    """Small set of domestic + export customers."""
    customers = [
        (1, "NZ Timber Co", "Domestic", 1),
        (2, "HB Lumber Ltd", "Domestic", 2),
        (3, "Saigon Builders", "Export", 4),
        (4, "Shanghai Wood Corp", "Export", 5),
        (5, "Tokyo Timber Group", "Export", 6)
    ]

    df = pd.DataFrame(customers, columns=[
        "customer_key", "customer_name", "segment", "region_key"
    ])
    return df


# ---------------------------------------------------------------
# 6. Generate Fact_Production
# ---------------------------------------------------------------

def generate_fact_production(dim_date, dim_site, dim_product):
    """Create 1 row per day–site–product with realistic volumes."""

    # Filter only mill sites (production happens at mills)
    mills = dim_site[dim_site["site_type"] == "Mill"]

    rows = []

    for _, row_site in mills.iterrows():
        for _, row_prod in dim_product.iterrows():
            # Only timber + logs processed in mills
            if row_prod["product_type"] not in ["Log", "Timber"]:
                continue

            for _, row_date in dim_date.iterrows():
                # Seasonality multiplier
                month = row_date["month"]
                if month in [6,7,8]:      # winter slowdown
                    season_factor = 0.7
                elif month in [12,1,2]:  # summer strong
                    season_factor = 1.2
                else:
                    season_factor = 1.0

                # Random base production
                input_vol = np.random.normal(row_site["capacity_m3"] * season_factor, 50)
                input_vol = max(input_vol, 100)

                # Yield varies by product type
                if row_prod["product_type"] == "Log":
                    yield_rate = 0.85
                else:
                    yield_rate = 0.90

                output_vol = input_vol * yield_rate

                # Downtime (random spikes)
                downtime = max(np.random.normal(1, 0.5), 0)
                if random.random() < 0.02:  # 2% chance anomaly
                    downtime += 5  # Big downtime spike

                shift_hours = 24
                energy = output_vol * np.random.normal(1.5, 0.1)

                rows.append([
                    row_date["date_key"],
                    row_site["site_key"],
                    row_prod["product_key"],
                    round(input_vol, 1),
                    round(output_vol, 1),
                    round(downtime, 2),
                    shift_hours,
                    round(energy, 2)
                ])

    df = pd.DataFrame(rows, columns=[
        "date_key", "site_key", "product_key",
        "input_volume_m3", "output_volume_m3",
        "downtime_hours", "shift_hours", "energy_kwh"
    ])

    return df


# ---------------------------------------------------------------
# 7. Generate Fact_Shipment
# ---------------------------------------------------------------

def generate_fact_shipment(dim_date, dim_customer, dim_product, dim_site):
    """Create synthetic shipments with delays and export patterns."""

    shipments = []
    order_id_counter = 100000

    # Choose only ports as shipping origin
    ports = dim_site[dim_site["site_type"] == "Port"]

    for _ in range(4000):  # number of shipments
        order_id = f"ORD{order_id_counter}"
        order_id_counter += 1

        customer = dim_customer.sample(1).iloc[0]
        product = dim_product.sample(1).iloc[0]
        port = ports.sample(1).iloc[0]

        # Pick a random order date
        rand_date = dim_date.sample(1).iloc[0]
        order_key = rand_date["date_key"]

        # Ship date = order + 1–7 days
        ship_offset = np.random.randint(1, 8)
        ship_date = rand_date["date"] + timedelta(days=ship_offset)
        ship_key = int(ship_date.strftime("%Y%m%d"))

        # Delivery date = ship + 3–20 days
        delivery_offset = np.random.randint(3, 21)
        delivery_date = ship_date + timedelta(days=delivery_offset)
        delivery_key = int(delivery_date.strftime("%Y%m%d"))

        # On-time logic
        on_time = 1 if delivery_offset <= 10 else 0
        in_full = 1 if random.random() > 0.05 else 0  # 5% incomplete

        qty = max(np.random.normal(50, 10), 10)

        shipments.append([
            order_id, order_key, ship_key, delivery_key,
            customer["customer_key"], product["product_key"], port["site_key"],
            round(qty, 1), on_time, in_full
        ])

    df = pd.DataFrame(shipments, columns=[
        "order_id", "order_date_key", "ship_date_key", "delivery_date_key",
        "customer_key", "product_key", "site_key",
        "qty_m3", "on_time_flag", "in_full_flag"
    ])

    return df


# ---------------------------------------------------------------
# 8. Generate Fact_Finance
# ---------------------------------------------------------------

def generate_fact_finance(dim_product, dim_region):
    """Monthly finance metrics with revenue & margin variability."""
    rows = []

    months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")

    for month in months:
        month_key = int(month.strftime("%Y%m"))

        for _, prod in dim_product.iterrows():
            for _, reg in dim_region.iterrows():

                # Revenue pattern: timber > log > pulp
                base_rev = {
                    "Timber": 300000,
                    "Log": 200000,
                    "Pulp": 150000
                }.get(prod["product_type"], 100000)

                # Add noise
                revenue = np.random.normal(base_rev, 50000)

                direct_cost = revenue * np.random.uniform(0.55, 0.75)
                opex = revenue * np.random.uniform(0.05, 0.15)

                # Budget: slightly optimistic
                budget_rev = base_rev * np.random.uniform(1.02, 1.07)
                budget_cost = budget_rev * np.random.uniform(0.6, 0.7)

                rows.append([
                    month_key,
                    prod["product_key"],
                    reg["region_key"],
                    round(revenue, 2),
                    round(direct_cost, 2),
                    round(opex, 2),
                    round(budget_rev, 2),
                    round(budget_cost, 2)
                ])

    df = pd.DataFrame(rows, columns=[
        "month_key", "product_key", "region_key",
        "revenue_nzd", "direct_cost_nzd", "opex_nzd",
        "budget_revenue_nzd", "budget_cost_nzd"
    ])

    return df


# ---------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------

if __name__ == "__main__":
    dim_date = generate_dim_date()
    dim_region = generate_dim_region()
    dim_site = generate_dim_site()
    dim_product = generate_dim_product()
    dim_customer = generate_dim_customer()

    fact_prod = generate_fact_production(dim_date, dim_site, dim_product)
    fact_ship = generate_fact_shipment(dim_date, dim_customer, dim_product, dim_site)
    fact_fin  = generate_fact_finance(dim_product, dim_region)

    # Save as CSV
    dim_date.to_csv("data/Dim_Date.csv", index=False)
    dim_region.to_csv("data/Dim_Region.csv", index=False)
    dim_site.to_csv("data/Dim_Site.csv", index=False)
    dim_product.to_csv("data/Dim_Product.csv", index=False)
    dim_customer.to_csv("data/Dim_Customer.csv", index=False)

    fact_prod.to_csv("data/Fact_Production.csv", index=False)
    fact_ship.to_csv("data/Fact_Shipment.csv", index=False)
    fact_fin.to_csv("data/Fact_Finance.csv", index=False)

    print(">>> Synthetic PanPac dataset generated!")
