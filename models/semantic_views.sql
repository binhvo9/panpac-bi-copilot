-- =========================================================
-- Production Metrics Layer
-- =========================================================

CREATE OR REPLACE VIEW vw_production AS
SELECT
    d.date,
    d.month,
    d.year,
    s.site_name,
    p.product_name,
    f.input_volume_m3,
    f.output_volume_m3,
    f.downtime_hours,
    f.energy_kwh,
    (f.output_volume_m3 / f.input_volume_m3) AS yield_pct
FROM Fact_Production f
JOIN Dim_Date d       ON f.date_key = d.date_key
JOIN Dim_Site s       ON f.site_key = s.site_key
JOIN Dim_Product p    ON f.product_key = p.product_key;


-- =========================================================
-- Shipment Metrics Layer
-- =========================================================

CREATE OR REPLACE VIEW vw_shipments AS
SELECT
    s.order_id,
    d1.date AS order_date,
    d2.date AS ship_date,
    d3.date AS delivery_date,
    c.customer_name,
    p.product_name,
    si.site_name,
    s.qty_m3,
    s.on_time_flag,
    s.in_full_flag,
    (s.on_time_flag * s.in_full_flag) AS otif_flag,
    DATE_DIFF('day', d1.date, d3.date) AS lead_time_days
FROM Fact_Shipment s
JOIN Dim_Date d1 ON s.order_date_key = d1.date_key
JOIN Dim_Date d2 ON s.ship_date_key = d2.date_key
JOIN Dim_Date d3 ON s.delivery_date_key = d3.date_key
JOIN Dim_Product p ON s.product_key = p.product_key
JOIN Dim_Customer c ON s.customer_key = c.customer_key
JOIN Dim_Site si ON s.site_key = si.site_key;


-- =========================================================
-- Finance Metrics Layer
-- =========================================================

CREATE OR REPLACE VIEW vw_finance AS
SELECT
    f.month_key,
    pr.product_name,
    r.region_name,
    f.revenue_nzd,
    f.direct_cost_nzd,
    f.opex_nzd,
    (f.revenue_nzd - f.direct_cost_nzd) AS gross_profit,
    (f.revenue_nzd - f.direct_cost_nzd) / f.revenue_nzd AS gross_margin_pct,
    (f.revenue_nzd - f.direct_cost_nzd - f.opex_nzd) AS ebitda,
    (f.revenue_nzd - f.direct_cost_nzd - f.opex_nzd) / f.revenue_nzd AS ebitda_margin_pct
FROM Fact_Finance f
JOIN Dim_Product pr ON f.product_key = pr.product_key
JOIN Dim_Region r   ON f.region_key = r.region_key;
