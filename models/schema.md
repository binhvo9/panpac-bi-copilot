
# ✅ **models/schema.md (FULL FILE — copy 100%)**

```markdown
# PANPAC BI DATA MODEL – SCHEMA DOCUMENTATION
This file defines the full semantic data model for the PanPac BI Copilot project.

It includes:
- Dimension tables
- Fact tables
- Grain (what 1 row means)
- Join keys
- Column definitions
- Notes for Tableau + DuckDB

This is the “source of truth” for the entire BI project.


# ============================================================
# 1. DIMENSION TABLES (CONFORMED)
# ============================================================

## 1.1 Dim_Date
**Purpose:** Shared calendar table for all fact tables.  
**Grain:** One row per day.

| Column Name | Type | Description |
|-------------|------|-------------|
| date_key | INT | Primary key in YYYYMMDD format |
| date | DATE | Actual date |
| day | INT | Day of month |
| month | INT | Month number |
| month_name | TEXT | Month name (Jan, Feb...) |
| quarter | INT | Quarter number |
| year | INT | Calendar year |
| weekday | INT | Day of week (1–7) |
| weekday_name | TEXT | Name of weekday |

**Join Key:** `date_key`

---

## 1.2 Dim_Site
**Purpose:** Standard list of locations (forests, mills, ports).  
**Grain:** One row per site.

| Column | Type | Description |
|--------|------|-------------|
| site_key | INT | Primary key |
| site_name | TEXT | Name of mill/forest/port |
| site_type | TEXT | forest / mill / port |
| region_key | INT | Foreign key to Dim_Region |
| capacity | INT | Optional (shift capacity / per day) |

**Join Key:** `site_key`

---

## 1.3 Dim_Product
**Purpose:** Standardized products across operations, supply chain, finance.  
**Grain:** One row per product.

| Column | Type | Description |
|--------|------|-------------|
| product_key | INT | Primary key |
| product_name | TEXT | Product display name |
| product_type | TEXT | log / timber / pulp |
| grade | TEXT | Forestry grade classification |
| unit_of_measure | TEXT | Usually m3 (cubic metres) |

**Join Key:** `product_key`

---

## 1.4 Dim_Customer
**Purpose:** Customer master table.  
**Grain:** One row per customer.

| Column | Type | Description |
|--------|------|-------------|
| customer_key | INT | Primary key |
| customer_name | TEXT | Legal customer name |
| region_key | INT | Region for finance + logistics |

**Join Key:** `customer_key`

---

## 1.5 Dim_Region
**Purpose:** Region table for drill-down in dashboards.  
**Grain:** One row per region.

| Column | Type | Description |
|--------|------|-------------|
| region_key | INT | Primary key |
| region_name | TEXT | NZ, APAC, China, North America |
| country | TEXT | Optional |

**Join Key:** `region_key`


---

# ============================================================
# 2. FACT TABLES
# ============================================================

## 2.1 Fact_Production (Operations)
**Grain:**  
➡️ One row per **day – site – product** combination.

**Meaning:**  
“This table shows production performance at each mill/forest every day.”

| Column | Type | Description |
|--------|------|-------------|
| date_key | INT | FK → Dim_Date |
| site_key | INT | FK → Dim_Site |
| product_key | INT | FK → Dim_Product |
| input_volume_m3 | FLOAT | Raw log volume entering mill |
| output_volume_m3 | FLOAT | Finished product volume |
| downtime_hours | FLOAT | Hours machine was down |
| shift_hours | FLOAT | Total scheduled shift hours |
| energy_kwh | FLOAT | Energy consumption |

**Primary Keys:** (date_key, site_key, product_key)

**KPIs produced from this fact:**
- Yield %
- Downtime %
- Energy intensity


---

## 2.2 Fact_Shipment (Supply Chain)
**Grain:**  
➡️ One row per **shipment order**.

**Meaning:**  
“Each row = one customer order shipped out.”

| Column | Type | Description |
|--------|------|-------------|
| order_id | INT | Primary key |
| customer_key | INT | FK → Dim_Customer |
| product_key | INT | FK → Dim_Product |
| site_key | INT | FK → Dim_Site (origin mill or port) |
| order_date_key | INT | FK → Dim_Date |
| ship_date_key | INT | FK → Dim_Date |
| delivery_date_key | INT | FK → Dim_Date |
| qty_m3 | FLOAT | Volume shipped |
| on_time_flag | INT | 1 = on time, 0 = late |
| in_full_flag | INT | 1 = complete, 0 = short |

**KPIs produced:**
- OTIF %
- On-Time Delivery %
- In-Full Delivery %
- Lead Time (days)


---

## 2.3 Fact_Finance (Finance)
**Grain:**  
➡️ One row per **month – product – region**.

**Meaning:**  
“Monthly financial performance by product and region.”

| Column | Type | Description |
|--------|------|-------------|
| date_key | INT | FK → Dim_Date (use first day of month) |
| product_key | INT | FK → Dim_Product |
| region_key | INT | FK → Dim_Region |
| revenue | FLOAT | Sales dollars |
| direct_cost | FLOAT | Cost of goods sold |
| opex | FLOAT | Operating expenses |
| budget_revenue | FLOAT | Planned revenue |
| budget_cost | FLOAT | Planned costs |

**KPIs produced:**
- Revenue
- Gross Margin %
- EBITDA Margin %


---

# ============================================================
# 3. JOIN RELATIONSHIPS
# ============================================================

This model uses **conformed dimensions** so Tableau can drill across fact tables.

### 3.1 Common Join Keys
| Dimension | Fact Tables Used In |
|-----------|----------------------|
| Dim_Date | All facts |
| Dim_Product | All facts |
| Dim_Region | Fact_Finance, (via site/customer) |
| Dim_Site | Fact_Production, Fact_Shipment |
| Dim_Customer | Fact_Shipment |

### 3.2 Example Join Logic

```

Fact_Production.date_key = Dim_Date.date_key
Fact_Production.site_key = Dim_Site.site_key
Fact_Production.product_key = Dim_Product.product_key

Fact_Shipment.customer_key = Dim_Customer.customer_key
Fact_Shipment.product_key = Dim_Product.product_key

Fact_Finance.product_key = Dim_Product.product_key
Fact_Finance.region_key  = Dim_Region.region_key

```


---

# ============================================================
# 4. NOTES FOR TABLEAU
# ============================================================

### ✔ Tableau “Relationships” Mode
Use Relationships between:
- Fact_Production ↔ Dim tables  
- Fact_Shipment ↔ Dim tables  
- Fact_Finance ↔ Dim tables  

Let Tableau handle joins automatically using join keys.

### ✔ Keep grain consistent
If Tableau metrics look wrong → check:
- wrong grain  
- missing keys  
- blending instead of joining  

### ✔ This schema is optimized for:
- KPI drilldown  
- Cross-domain insights  
- Executive dashboards  
- Self-service BI  


---

# ============================================================
# 5. WHY THIS MODEL WORKS
# ============================================================

- Uses **conformed dimensions** → enterprise-grade BI  
- Three “domain fact tables” → operations, logistics, finance  
- Clean grains → high KPI accuracy  
- Tableau-ready semantic structure  
- DuckDB-friendly star schema  
- KPI governance foundation  
- Easy to extend for Insight Agent (AI layer)  


---

# END OF SCHEMA DOCUMENT
```
