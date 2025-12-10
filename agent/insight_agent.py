# ============================================================
# Insight Agent for PanPac BI (Pure Python)
#
# This script:
#  - Connects to DuckDB semantic views:
#       vw_production, vw_shipments, vw_finance
#  - Calculates key KPIs for the latest date/month
#  - Compares them to a recent baseline
#  - Generates a simple plain-English "Daily BI Briefing"
#  - Saves the briefing as Markdown in ./reports/
#
# You can:
#   - Run it from command line: python agent/insight_agent.py
#   - Import generate_insight_report() in other Python code
# ============================================================

import duckdb
import pandas as pd
from datetime import datetime, timedelta
import os

# Connect to DuckDB database
CON = duckdb.connect("duckdb/panpac.duckdb")

# Make sure reports folder exists
os.makedirs("reports", exist_ok=True)


# ------------------------------------------------------------
# Helper: get latest available dates/months
# ------------------------------------------------------------

def get_latest_production_date():
    """Return the latest date available in vw_production."""
    df = CON.execute("SELECT max(date) AS max_date FROM vw_production").fetchdf()
    return pd.to_datetime(df["max_date"].iloc[0]).date()


def get_latest_shipment_date():
    """Return the latest order_date available in vw_shipments."""
    df = CON.execute("SELECT max(order_date) AS max_date FROM vw_shipments").fetchdf()
    return pd.to_datetime(df["max_date"].iloc[0]).date()


def get_latest_finance_month():
    """Return the latest month_key available in vw_finance as a date (first of month)."""
    df = CON.execute("SELECT max(month_key) AS max_month FROM vw_finance").fetchdf()
    max_month_key = int(df["max_month"].iloc[0])
    # month_key is in format YYYYMM, we convert to datetime
    return pd.to_datetime(str(max_month_key) + "01", format="%Y%m%d").date()


# ------------------------------------------------------------
# Operations KPIs: latest vs rolling baseline
# ------------------------------------------------------------

def get_operations_kpis(latest_date, window_days=7):
    """
    Calculate:
      - KPIs for latest_date
      - Rolling-average KPIs for previous N days (baseline)
    """
    # latest day metrics
    query_latest = """
        SELECT
            AVG(yield_pct) AS avg_yield,
            SUM(output_volume_m3) AS total_output,
            AVG(downtime_hours) AS avg_downtime
        FROM vw_production
        WHERE date = ?
    """
    df_latest = CON.execute(query_latest, [latest_date]).fetchdf()

    # baseline window: previous N days
    baseline_start = latest_date - timedelta(days=window_days)
    baseline_end = latest_date - timedelta(days=1)

    query_base = """
        SELECT
            AVG(yield_pct) AS avg_yield,
            SUM(output_volume_m3) AS total_output,
            AVG(downtime_hours) AS avg_downtime
        FROM vw_production
        WHERE date BETWEEN ? AND ?
    """
    df_base = CON.execute(query_base, [baseline_start, baseline_end]).fetchdf()

    latest = df_latest.iloc[0].to_dict()
    baseline = df_base.iloc[0].to_dict()

    return latest, baseline


# ------------------------------------------------------------
# Supply Chain KPIs: OTIF & Lead Time
# ------------------------------------------------------------

def get_supply_chain_kpis(latest_date, window_days=30):
    """
    Calculate shipment KPIs for:
      - Recent window (latest_date - window_days .. latest_date)
      - Previous window before that (for baseline)
    """

    # Current window
    cur_start = latest_date - timedelta(days=window_days)
    cur_end = latest_date

    query_cur = """
        SELECT
            AVG(otif_flag)       AS otif,
            AVG(on_time_flag)    AS on_time,
            AVG(in_full_flag)    AS in_full,
            AVG(lead_time_days)  AS avg_lead_time
        FROM vw_shipments
        WHERE order_date BETWEEN ? AND ?
    """
    df_cur = CON.execute(query_cur, [cur_start, cur_end]).fetchdf()

    # Baseline window: previous window_days days before current
    base_start = latest_date - timedelta(days=2 * window_days)
    base_end = latest_date - timedelta(days=window_days + 1)

    df_base = CON.execute(query_cur, [base_start, base_end]).fetchdf()

    current = df_cur.iloc[0].to_dict()
    baseline = df_base.iloc[0].to_dict()

    return current, baseline


# ------------------------------------------------------------
# Finance KPIs: latest month vs previous months
# ------------------------------------------------------------

def get_finance_kpis(latest_month_date, months_back=3):
    """
    Finance metrics:
      - Latest month KPIs
      - Average KPIs over previous 'months_back' months
    """
    latest_month_key = int(latest_month_date.strftime("%Y%m"))

    # latest month
    query_latest = """
        SELECT
            SUM(revenue_nzd)              AS total_revenue,
            AVG(gross_margin_pct)         AS avg_gross_margin,
            AVG(ebitda_margin_pct)        AS avg_ebitda_margin
        FROM vw_finance
        WHERE month_key = ?
    """
    df_latest = CON.execute(query_latest, [latest_month_key]).fetchdf()

    # baseline = previous N months
    # convert to month_key list like [202404, 202405, 202406]
    baseline_months = []
    year = latest_month_date.year
    month = latest_month_date.month
    for i in range(1, months_back + 1):
        # move back i months
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        baseline_months.append(int(f"{y}{m:02d}"))

    query_base = f"""
        SELECT
            AVG(total_revenue)      AS total_revenue,
            AVG(avg_gross_margin)   AS avg_gross_margin,
            AVG(avg_ebitda_margin)  AS avg_ebitda_margin
        FROM (
            SELECT
                month_key,
                SUM(revenue_nzd)             AS total_revenue,
                AVG(gross_margin_pct)        AS avg_gross_margin,
                AVG(ebitda_margin_pct)       AS avg_ebitda_margin
            FROM vw_finance
            WHERE month_key IN ({",".join(["?"] * len(baseline_months))})
            GROUP BY month_key
        )
    """
    df_base = CON.execute(query_base, baseline_months).fetchdf()

    latest = df_latest.iloc[0].to_dict()
    baseline = df_base.iloc[0].to_dict()

    return latest, baseline


# ------------------------------------------------------------
# Utility: safe percent change
# ------------------------------------------------------------

def percent_change(current, baseline):
    """Return percentage change from baseline to current (in % points)."""
    if baseline is None or baseline == 0:
        return None
    return (current - baseline) / baseline * 100.0


# ------------------------------------------------------------
# Generate narrative text from KPI comparisons
# ------------------------------------------------------------

def generate_operations_summary(latest, baseline):
    """Create a short text summary for Operations."""
    lines = []
    ly = latest["avg_yield"]
    by = baseline["avg_yield"]
    dy = percent_change(ly, by)

    lo = latest["total_output"]
    bo = baseline["total_output"]
    do = percent_change(lo, bo)

    ld = latest["avg_downtime"]
    bd = baseline["avg_downtime"]
    dd = percent_change(ld, bd)

    # Yield
    if dy is not None:
        if dy < -2:
            lines.append(f"- Yield decreased to {ly*100:.1f}% ({dy:.1f}% vs 7-day average).")
        elif dy > 2:
            lines.append(f"- Yield improved to {ly*100:.1f}% (+{dy:.1f}% vs 7-day average).")
        else:
            lines.append(f"- Yield is stable around {ly*100:.1f}% vs 7-day average.")

    # Output
    if do is not None:
        if do < -5:
            lines.append(f"- Total output softened to {lo:,.0f} m³ ({do:.1f}% vs 7-day average).")
        elif do > 5:
            lines.append(f"- Total output increased to {lo:,.0f} m³ (+{do:.1f}% vs 7-day average).")
        else:
            lines.append(f"- Total output is broadly in line with the 7-day average ({lo:,.0f} m³).")

    # Downtime
    if dd is not None:
        if dd > 10:
            lines.append(f"- Downtime increased to {ld:.2f} hrs/day (+{dd:.1f}% vs 7-day average).")
        elif dd < -10:
            lines.append(f"- Downtime improved to {ld:.2f} hrs/day ({dd:.1f}% vs 7-day average).")
        else:
            lines.append(f"- Downtime is roughly stable at {ld:.2f} hrs/day.")

    return lines


def generate_supply_chain_summary(current, baseline):
    """Create a short text summary for Supply Chain."""
    lines = []

    # OTIF
    cotif = current["otif"]
    botif = baseline["otif"]
    dotif = percent_change(cotif, botif) if botif is not None else None

    if dotif is not None:
        if dotif < -3:
            lines.append(f"- OTIF dropped to {cotif*100:.1f}% ({dotif:.1f}% vs prior 30 days).")
        elif dotif > 3:
            lines.append(f"- OTIF improved to {cotif*100:.1f}% (+{dotif:.1f}% vs prior 30 days).")
        else:
            lines.append(f"- OTIF remains stable around {cotif*100:.1f}% vs prior 30 days.")

    # Lead time
    clt = current["avg_lead_time"]
    blt = baseline["avg_lead_time"]
    dlt = percent_change(clt, blt) if blt is not None else None

    if dlt is not None:
        if dlt > 5:
            lines.append(f"- Average lead time increased to {clt:.1f} days ({dlt:.1f}% vs baseline).")
        elif dlt < -5:
            lines.append(f"- Average lead time improved to {clt:.1f} days ({dlt:.1f}% vs baseline).")
        else:
            lines.append(f"- Lead time is broadly stable at {clt:.1f} days.")

    return lines


def generate_finance_summary(latest, baseline, latest_month_date):
    """Create a short text summary for Finance."""
    lines = []

    lr = latest["total_revenue"]
    br = baseline["total_revenue"]
    dr = percent_change(lr, br) if br is not None else None

    lgm = latest["avg_gross_margin"]
    bgm = baseline["avg_gross_margin"]
    dgm = percent_change(lgm, bgm) if bgm is not None else None

    leb = latest["avg_ebitda_margin"]
    beb = baseline["avg_ebitda_margin"]
    deb = percent_change(leb, beb) if beb is not None else None

    month_label = latest_month_date.strftime("%B %Y")

    lines.append(f"- For {month_label}, total revenue is ${lr:,.0f}.")

    if dgm is not None:
        if dgm < -3:
            lines.append(
                f"- Gross margin eased to {lgm*100:.1f}% ({dgm:.1f}% vs prior months)."
            )
        elif dgm > 3:
            lines.append(
                f"- Gross margin improved to {lgm*100:.1f}% (+{dgm:.1f}% vs prior months)."
            )
        else:
            lines.append(
                f"- Gross margin is stable around {lgm*100:.1f}% versus recent months."
            )

    if deb is not None:
        if deb < -3:
            lines.append(
                f"- EBITDA margin softened to {leb*100:.1f}% ({deb:.1f}% vs prior months)."
            )
        elif deb > 3:
            lines.append(
                f"- EBITDA margin strengthened to {leb*100:.1f}% (+{deb:.1f}% vs prior months)."
            )
        else:
            lines.append(
                f"- EBITDA margin is broadly stable at {leb*100:.1f}%."
            )

    return lines


# ------------------------------------------------------------
# Main function to generate full markdown report
# ------------------------------------------------------------

def generate_insight_report(run_date=None):
    """
    Generate a markdown string with BI insights for:
      - Operations
      - Supply Chain
      - Finance
    run_date: optional. If None, uses 'today' in system time (only for header label).
    """
    if run_date is None:
        run_date = datetime.today().date()

    # Latest available points in data
    latest_ops_date = get_latest_production_date()
    latest_ship_date = get_latest_shipment_date()
    latest_fin_month_date = get_latest_finance_month()

    # Fetch KPIs and baselines
    ops_latest, ops_base = get_operations_kpis(latest_ops_date)
    sc_cur, sc_base = get_supply_chain_kpis(latest_ship_date)
    fin_latest, fin_base = get_finance_kpis(latest_fin_month_date)

    # Build markdown
    lines = []
    lines.append(f"# PanPac Daily BI Briefing")
    lines.append(f"_Generated on {run_date.isoformat()}_")
    lines.append("")
    lines.append(f"**Data as of:**")
    lines.append(f"- Operations: {latest_ops_date.isoformat()}")
    lines.append(f"- Supply Chain: {latest_ship_date.isoformat()}")
    lines.append(f"- Finance: {latest_fin_month_date.strftime('%B %Y')}")
    lines.append("")

    # Operations section
    lines.append("## 1. Operations – Mills & Yield")
    ops_lines = generate_operations_summary(ops_latest, ops_base)
    if ops_lines:
        lines.extend(ops_lines)
    else:
        lines.append("- No operations data available for this period.")
    lines.append("")

    # Supply Chain section
    lines.append("## 2. Supply Chain – OTIF & Lead Time")
    sc_lines = generate_supply_chain_summary(sc_cur, sc_base)
    if sc_lines:
        lines.extend(sc_lines)
    else:
        lines.append("- No shipment data available for this period.")
    lines.append("")

    # Finance section
    lines.append("## 3. Finance – Revenue & Margins")
    fin_lines = generate_finance_summary(fin_latest, fin_base, latest_fin_month_date)
    if fin_lines:
        lines.extend(fin_lines)
    else:
        lines.append("- No finance data available for this period.")
    lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# Run as script: create markdown file in ./reports/
# ------------------------------------------------------------

if __name__ == "__main__":
    today = datetime.today().date()
    md = generate_insight_report(today)

    # Save to file
    out_name = f"reports/insight_{today.strftime('%Y%m%d')}.md"
    with open(out_name, "w", encoding="utf-8") as f:
        f.write(md)

    print(f">>> Insight report generated: {out_name}")
    print()
    print(md)
