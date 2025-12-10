# ============================================================
# PanPac BI Dashboard - Pure Python (Streamlit)
#
# - Connects to DuckDB semantic views:
#   vw_production, vw_shipments, vw_finance
# - Shows 3 main pages:
#   1. Operations (Yield & Volume by Mill)
#   2. Supply Chain (OTIF & Lead Time)
#   3. Finance (Revenue & Margins)
#
# This is portfolio-ready: clean, simple, and easy to explain.
# ============================================================

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st
import os
import sys

# Add project root (panpac-bi-copilot) to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.insight_agent import generate_insight_report

from agent.ai_recommender import generate_ai_recommendations


# -------------------------------------------
# 1. Set up connection to DuckDB
# -------------------------------------------

# We connect once, and reuse the connection
CON = duckdb.connect("duckdb/panpac.duckdb")


# -------------------------------------------
# 2. Helper functions to fetch data
#    We cache them so the app is faster.
# -------------------------------------------

@st.cache_data
def load_production():
    """Load production view from DuckDB as a pandas DataFrame."""
    query = "SELECT * FROM vw_production"
    df = CON.execute(query).fetchdf()
    return df


@st.cache_data
def load_shipments():
    """Load shipments view from DuckDB as a pandas DataFrame."""
    query = "SELECT * FROM vw_shipments"
    df = CON.execute(query).fetchdf()
    return df


@st.cache_data
def load_finance():
    """Load finance view from DuckDB as a pandas DataFrame."""
    query = "SELECT * FROM vw_finance"
    df = CON.execute(query).fetchdf()
    return df


# -------------------------------------------
# 3. Page builders (one function per page)
# -------------------------------------------

def page_operations():
    """Operations page: Yield, volume, downtime by mill."""
    st.header("Operations – Mill Performance & Yield")

    df = load_production()

    # Convert date column to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    # Sidebar filters for Operations page
    st.sidebar.subheader("Filters – Operations")
    site_filter = st.sidebar.multiselect(
        "Select mills (site_name):",
        options=sorted(df["site_name"].unique()),
        default=list(df["site_name"].unique())
    )

    product_filter = st.sidebar.multiselect(
        "Select products:",
        options=sorted(df["product_name"].unique()),
        default=list(df["product_name"].unique())
    )

    # Apply filters
    df_filtered = df[df["site_name"].isin(site_filter) &
                     df["product_name"].isin(product_filter)]

    # ---- KPI cards ----
    st.subheader("Key KPIs")

    total_output = df_filtered["output_volume_m3"].sum()
    avg_yield = df_filtered["yield_pct"].mean()
    avg_downtime = df_filtered["downtime_hours"].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Output (m³)", f"{total_output:,.0f}")
    col2.metric("Average Yield (%)", f"{avg_yield*100:,.1f}%")
    col3.metric("Avg Downtime (hrs/day)", f"{avg_downtime:,.2f}")

    # ---- Yield over time by mill ----
    st.subheader("Yield % over time by mill")

    # Group by date + site for smoother chart
    df_yield = (
        df_filtered
        .groupby(["date", "site_name"], as_index=False)["yield_pct"]
        .mean()
    )

    fig_yield = px.line(
        df_yield,
        x="date",
        y="yield_pct",
        color="site_name",
        labels={"yield_pct": "Yield %", "site_name": "Mill"},
        title="Yield % by Mill over Time"
    )
    fig_yield.update_yaxes(tickformat=".1%")  # show as percentage

    st.plotly_chart(fig_yield, use_container_width=True)

    # ---- Output by mill ----
    st.subheader("Total Output by Mill")

    df_output = (
        df_filtered
        .groupby("site_name", as_index=False)["output_volume_m3"]
        .sum()
        .sort_values("output_volume_m3", ascending=False)
    )

    fig_output = px.bar(
        df_output,
        x="site_name",
        y="output_volume_m3",
        labels={"site_name": "Mill", "output_volume_m3": "Output (m³)"},
        title="Total Output by Mill"
    )

    st.plotly_chart(fig_output, use_container_width=True)

    # Optional raw data table
    with st.expander("Show raw Operations data"):
        st.dataframe(df_filtered)


def page_supply_chain():
    """Supply Chain page: OTIF %, on-time, in-full, lead time."""
    st.header("Supply Chain – OTIF & Lead Time")

    df = load_shipments()

    # Convert date columns to datetime
    for col in ["order_date", "ship_date", "delivery_date"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col])

    # Sidebar filters
    st.sidebar.subheader("Filters – Supply Chain")
    customer_filter = st.sidebar.multiselect(
        "Select customers:",
        options=sorted(df["customer_name"].unique()),
        default=list(df["customer_name"].unique())
    )

    product_filter = st.sidebar.multiselect(
        "Select products:",
        options=sorted(df["product_name"].unique()),
        default=list(df["product_name"].unique())
    )

    df_filtered = df[df["customer_name"].isin(customer_filter) &
                     df["product_name"].isin(product_filter)]

    # ---- KPI cards ----
    st.subheader("Key KPIs")

    otif = df_filtered["otif_flag"].mean()
    on_time = df_filtered["on_time_flag"].mean()
    in_full = df_filtered["in_full_flag"].mean()
    avg_lead = df_filtered["lead_time_days"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("OTIF %", f"{otif*100:,.1f}%")
    col2.metric("On-Time %", f"{on_time*100:,.1f}%")
    col3.metric("In-Full %", f"{in_full*100:,.1f}%")
    col4.metric("Avg Lead Time (days)", f"{avg_lead:,.1f}")

    # ---- OTIF by customer ----
    st.subheader("OTIF % by Customer")

    df_otif_cust = (
        df_filtered
        .groupby("customer_name", as_index=False)["otif_flag"]
        .mean()
        .sort_values("otif_flag", ascending=False)
    )

    fig_otif = px.bar(
        df_otif_cust,
        x="customer_name",
        y="otif_flag",
        labels={"customer_name": "Customer", "otif_flag": "OTIF %"},
        title="OTIF % by Customer"
    )
    fig_otif.update_yaxes(tickformat=".1%")

    st.plotly_chart(fig_otif, use_container_width=True)

    # ---- Lead time distribution ----
    st.subheader("Lead Time Distribution")

    fig_lead = px.histogram(
        df_filtered,
        x="lead_time_days",
        nbins=20,
        labels={"lead_time_days": "Lead Time (days)"},
        title="Lead Time Distribution"
    )

    st.plotly_chart(fig_lead, use_container_width=True)

    # Optional raw data
    with st.expander("Show raw Shipment data"):
        st.dataframe(df_filtered)


def page_finance():
    """Finance page: revenue trends and margin by product/region."""
    st.header("Finance – Revenue & Margins")

    df = load_finance()

    # Create a proper datetime month field from month_key (YYYYMM)
    if "month_key" in df.columns:
        df["month"] = pd.to_datetime(df["month_key"].astype(str) + "01",
                                     format="%Y%m%d")

    # Sidebar filters
    st.sidebar.subheader("Filters – Finance")
    product_filter = st.sidebar.multiselect(
        "Select products:",
        options=sorted(df["product_name"].unique()),
        default=list(df["product_name"].unique())
    )

    region_filter = st.sidebar.multiselect(
        "Select regions:",
        options=sorted(df["region_name"].unique()),
        default=list(df["region_name"].unique())
    )

    df_filtered = df[df["product_name"].isin(product_filter) &
                     df["region_name"].isin(region_filter)]

    # ---- KPI cards ----
    st.subheader("Key KPIs")

    total_rev = df_filtered["revenue_nzd"].sum()
    avg_gm = df_filtered["gross_margin_pct"].mean()
    avg_ebitda = df_filtered["ebitda_margin_pct"].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue (NZD)", f"${total_rev:,.0f}")
    col2.metric("Avg Gross Margin %", f"{avg_gm*100:,.1f}%")
    col3.metric("Avg EBITDA Margin %", f"{avg_ebitda*100:,.1f}%")

    # ---- Revenue trend over time ----
    st.subheader("Revenue trend over time")

    df_rev = (
        df_filtered
        .groupby("month", as_index=False)["revenue_nzd"]
        .sum()
    )

    fig_rev = px.line(
        df_rev,
        x="month",
        y="revenue_nzd",
        labels={"month": "Month", "revenue_nzd": "Revenue (NZD)"},
        title="Total Revenue over Time"
    )

    st.plotly_chart(fig_rev, use_container_width=True)

    # ---- Margin by product ----
    st.subheader("Gross Margin % by Product")

    df_margin_prod = (
        df_filtered
        .groupby("product_name", as_index=False)["gross_margin_pct"]
        .mean()
        .sort_values("gross_margin_pct", ascending=False)
    )

    fig_margin = px.bar(
        df_margin_prod,
        x="product_name",
        y="gross_margin_pct",
        labels={"product_name": "Product", "gross_margin_pct": "Gross Margin %"},
        title="Gross Margin % by Product"
    )
    fig_margin.update_yaxes(tickformat=".1%")

    st.plotly_chart(fig_margin, use_container_width=True)

    with st.expander("Show raw Finance data"):
        st.dataframe(df_filtered)


def page_data_explorer():
    """Simple raw data explorer for all views."""
    st.header("Data Explorer")

    option = st.selectbox(
        "Choose a dataset to explore:",
        ["vw_production", "vw_shipments", "vw_finance"]
    )

    if option == "vw_production":
        df = load_production()
    elif option == "vw_shipments":
        df = load_shipments()
    else:
        df = load_finance()

    st.write(f"Showing first 100 rows of {option}:")
    st.dataframe(df.head(100))

def page_insight_agent():
    """Insight Agent page: auto-generated daily briefing + AI Copilot."""
    st.header("Insight Agent – Daily BI Briefing")

    # Date in header only (data itself uses latest from DB)
    run_date = st.date_input("Report generated on (display only):",
                             pd.to_datetime("today"))

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Generate Descriptive Insight (current)"):
            md = generate_insight_report(run_date)
            st.markdown(md)
            st.success("Descriptive insight report generated.")
    with col2:
        if st.button("Run AI Copilot (Diagnostic / Predictive / Prescriptive)"):
            ai_md = generate_ai_recommendations()
            st.markdown(ai_md)
            st.success("AI Copilot recommendations generated.")



# -------------------------------------------
# 4. Main app entry point
# -------------------------------------------

def main():
    # Sidebar navigation
    st.sidebar.title("PanPac BI – Python App")
    page = st.sidebar.radio(
        "Go to:",
        ["Operations", "Supply Chain", "Finance", "Insight Agent", "Data Explorer"]
    )

    if page == "Operations":
        page_operations()
    elif page == "Supply Chain":
        page_supply_chain()
    elif page == "Finance":
        page_finance()
    elif page == "Insight Agent":
        page_insight_agent()
    else:
        page_data_explorer()



if __name__ == "__main__":
    main()
