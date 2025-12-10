# ============================================================
# AI Recommender for PanPac BI
#
# Tiny "AI Copilot" that:
#  - Looks back (diagnostic)
#  - Learns a simple trend model (predictive)
#  - Outputs suggestions (prescriptive)
#
# Returns a markdown string for the Streamlit app.
# ============================================================

import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Connect to DuckDB (reuse same file)
CON = duckdb.connect("duckdb/panpac.duckdb")


# ------------------------------------------------------------
# Small helper: simple linear trend forecast
# ------------------------------------------------------------

def _trend_forecast(df, date_col, value_col, steps_ahead=1):
    """
    Simple linear regression on (time index -> value).
    - df: DataFrame with a date column and a metric column
    - steps_ahead: how many time steps into the future to predict
    Returns a single float or None if not enough data.
    """
    df = df[[date_col, value_col]].dropna().copy()
    if df.empty or len(df) < 5:  # not enough points
        return None

    df = df.sort_values(date_col)
    df["t"] = np.arange(len(df))  # time index 0,1,2,...

    X = df[["t"]].values
    y = df[value_col].values

    model = LinearRegression()
    model.fit(X, y)

    future_t = df["t"].iloc[-1] + steps_ahead
    pred = model.predict([[future_t]])[0]
    return float(pred)


def _pct_change(cur, base):
    """Safe percent change in %, return None if baseline is 0/None."""
    if base is None or base == 0 or np.isnan(base):
        return None
    return (cur - base) / base * 100.0


# ------------------------------------------------------------
# 1) Diagnostic – where are problems today?
# ------------------------------------------------------------

def _diagnostic_operations():
    """Find weakest mill in last 30 days (by yield and downtime)."""
    df = CON.execute("""
        SELECT date, site_name, yield_pct, downtime_hours
        FROM vw_production
    """).fetchdf()
    df["date"] = pd.to_datetime(df["date"])

    cutoff = df["date"].max() - pd.Timedelta(days=30)
    recent = df[df["date"] >= cutoff]

    if recent.empty:
        return "No recent operations data."

    # Lowest yield
    yield_by_site = recent.groupby("site_name")["yield_pct"].mean()
    worst_site = yield_by_site.idxmin()
    worst_yield = yield_by_site.min()
    avg_yield = yield_by_site.mean()

    # Highest downtime
    down_by_site = recent.groupby("site_name")["downtime_hours"].mean()
    high_d_site = down_by_site.idxmax()
    high_d = down_by_site.max()
    avg_d = down_by_site.mean()

    return (
        f"- Operations: Mill **{worst_site}** has the lowest yield "
        f"({worst_yield*100:.1f}% vs fleet avg {avg_yield*100:.1f}%) in the last 30 days.\n"
        f"- Downtime: Mill **{high_d_site}** carries the highest downtime "
        f"({high_d:.2f} hrs/day vs avg {avg_d:.2f} hrs)."
    )


def _diagnostic_supply_chain():
    """Find worst customer by OTIF in last 30 days."""
    df = CON.execute("""
        SELECT order_date, customer_name, otif_flag
        FROM vw_shipments
    """).fetchdf()
    df["order_date"] = pd.to_datetime(df["order_date"])

    cutoff = df["order_date"].max() - pd.Timedelta(days=30)
    recent = df[df["order_date"] >= cutoff]

    if recent.empty:
        return "No recent shipment data."

    otif_by_cust = recent.groupby("customer_name")["otif_flag"].mean()
    worst_cust = otif_by_cust.idxmin()
    worst_otif = otif_by_cust.min()
    avg_otif = otif_by_cust.mean()

    return (
        f"- Supply chain: Customer **{worst_cust}** has the weakest OTIF "
        f"({worst_otif*100:.1f}% vs overall {avg_otif*100:.1f}% in the last 30 days)."
    )


def _diagnostic_finance():
    """Find region with lowest gross margin over last 6 months."""
    df = CON.execute("""
        SELECT month_key, region_name, gross_margin_pct
        FROM vw_finance
    """).fetchdf()

    # Convert month_key to datetime (first of month)
    df["month"] = pd.to_datetime(df["month_key"].astype(str) + "01", format="%Y%m%d")

    cutoff = df["month"].max() - pd.DateOffset(months=6)
    recent = df[df["month"] >= cutoff]

    if recent.empty:
        return "No recent finance data."

    gm_by_region = recent.groupby("region_name")["gross_margin_pct"].mean()
    worst_region = gm_by_region.idxmin()
    worst_margin = gm_by_region.min()
    avg_margin = gm_by_region.mean()

    return (
        f"- Finance: Region **{worst_region}** has the weakest gross margin "
        f"({worst_margin*100:.1f}% vs overall {avg_margin*100:.1f}% over the last 6 months)."
    )


# ------------------------------------------------------------
# 2) Predictive – where are we heading?
# ------------------------------------------------------------

def _predictive_operations():
    """Forecast yield 7 days ahead using simple trend."""
    df = CON.execute("""
        SELECT date, AVG(yield_pct) AS avg_yield
        FROM vw_production
        GROUP BY date
    """).fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    if df.empty:
        return "No data to forecast operations."

    latest_yield = df["avg_yield"].iloc[-1]
    forecast_yield = _trend_forecast(df, "date", "avg_yield", steps_ahead=7)

    if forecast_yield is None:
        return "Not enough history to forecast operations."

    delta = _pct_change(forecast_yield, latest_yield)
    direction = "slightly" if delta and abs(delta) < 2 else "significantly"

    return (
        f"- Operations forecast: trend model suggests fleet yield could move to "
        f"{forecast_yield*100:.1f}% over the next week "
        f"({direction} change of {delta:.1f}% vs today)."
    )


def _predictive_supply_chain():
    """Forecast OTIF 30 days ahead based on daily trend."""
    df = CON.execute("""
        SELECT order_date, AVG(otif_flag) AS avg_otif
        FROM vw_shipments
        GROUP BY order_date
    """).fetchdf()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df = df.sort_values("order_date")

    if df.empty:
        return "No data to forecast OTIF."

    latest_otif = df["avg_otif"].iloc[-1]
    forecast_otif = _trend_forecast(df, "order_date", "avg_otif", steps_ahead=30)

    if forecast_otif is None:
        return "Not enough history to forecast OTIF."

    delta = _pct_change(forecast_otif, latest_otif)

    return (
        f"- OTIF forecast: model points to around {forecast_otif*100:.1f}% in ~1 month "
        f"({delta:.1f}% vs the latest level)."
    )


def _predictive_finance():
    """Forecast gross margin 3 months ahead based on monthly trend."""
    df = CON.execute("""
        SELECT month_key, AVG(gross_margin_pct) AS avg_gm
        FROM vw_finance
        GROUP BY month_key
    """).fetchdf()
    df["month"] = pd.to_datetime(df["month_key"].astype(str) + "01", format="%Y%m%d")
    df = df.sort_values("month")

    if df.empty:
        return "No data to forecast margins."

    latest_gm = df["avg_gm"].iloc[-1]
    forecast_gm = _trend_forecast(df, "month", "avg_gm", steps_ahead=3)

    if forecast_gm is None:
        return "Not enough history to forecast margins."

    delta = _pct_change(forecast_gm, latest_gm)

    return (
        f"- Margin forecast: gross margin could trend toward {forecast_gm*100:.1f}% "
        f"in the next 3 months ({delta:.1f}% vs the latest month)."
    )


# ------------------------------------------------------------
# 3) Prescriptive – what should we do?
# ------------------------------------------------------------

def _prescriptive_actions():
    """
    Convert patterns into simple recommended next actions.
    For POC we keep it rule-based and short.
    """
    actions = [
        "- Run a short root-cause session on the weakest mill: focus on top 1–2 downtime drivers and quick maintenance wins.",
        "- Sit down with the lowest-OTIF customer and map their order-to-delivery steps: agree on cut-off times and booking rules.",
        "- For the weakest-margin region, review price vs cost-to-serve and consider a small price uplift or a product mix shift.",
        "- Feed these patterns back into planning: use the forecast as a simple early-warning signal rather than a hard budget."
    ]
    return "\n".join(actions)


# ------------------------------------------------------------
# Public function: generate AI recommendations as markdown
# ------------------------------------------------------------

def generate_ai_recommendations():
    """
    Main entry: returns markdown string with:
    - Diagnostic
    - Predictive
    - Prescriptive
    """
    lines = []

    lines.append("## AI Copilot – Diagnostic, Predictive, Prescriptive")
    lines.append("")

    # Diagnostic
    lines.append("### 1. Diagnostic – What is driving performance?")
    lines.append(_diagnostic_operations())
    lines.append(_diagnostic_supply_chain())
    lines.append(_diagnostic_finance())
    lines.append("")

    # Predictive
    lines.append("### 2. Predictive – Where are we heading?")
    lines.append(_predictive_operations())
    lines.append(_predictive_supply_chain())
    lines.append(_predictive_finance())
    lines.append("")

    # Prescriptive
    lines.append("### 3. Prescriptive – What should we do next?")
    lines.append(_prescriptive_actions())
    lines.append("")

    return "\n".join(lines)


# If you want to test quickly:
if __name__ == "__main__":
    md = generate_ai_recommendations()
    print(md)
