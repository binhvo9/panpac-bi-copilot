# PanPac BI Copilot – AI-Assisted Forestry Business Intelligence

**Goal:** Demonstrate end-to-end BI capability for a renewables company (modeled on Pan Pac) – from business requirements and semantic modelling to dashboards, governance, and an AI-style Insight Agent.

This portfolio project is designed to match the responsibilities of a **Senior Business Analyst – Business Intelligence**:

- Shape a BI roadmap aligned with business priorities.
- Design a semantic model and KPI layer for operations, supply chain, and finance.
- Build intuitive, high-performance dashboards for decision makers.
- Define and document KPI rules, governance standards, and refresh strategies.
- Implement an automated "Insight Agent" that monitors key metrics and generates human-readable daily summaries.

Tech stack (Mac + free tools only):

- Python, pandas/polars, DuckDB/SQLite
- Streamlit + Plotly for interactive BI dashboards
- Markdown documentation for roadmap, governance, and training
- Simple rule-based Insight Agent (with optional LLM extension)


Operations – Mill Performance & Yield
![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)

Supply Chain – OTIF & Lead Time
![alt text](image-3.png)
![alt text](image-4.png)
![alt text](image-5.png)

Finance – Revenue & Margins
![alt text](image-6.png)
![alt text](image-7.png)
![alt text](image-8.png)

Data Explorer
![alt text](image-9.png)
![alt text](image-10.png)

## Insight Agent (AI-style BI Assistant)

On top of the semantic model and dashboards, I built a small Python-based "Insight Agent" that:

- Reads the latest KPIs from DuckDB (operations, supply chain, finance).
- Compares them to rolling baselines (7-day, 30-day, 3-month averages).
- Generates a plain-English BI briefing in Markdown.
- Can be triggered from the command line or from the Streamlit app.

This approximates how a BI Analyst would:
- Monitor production yield, OTIF and financial margins.
- Highlight anomalies or improvements.
- Communicate a short, actionable summary to business stakeholders.

Insight Agent – Daily BI Briefing
![alt text](image-11.png)
![alt text](image-12.png)
![alt text](image-13.png)

### AI Copilot Button – From Descriptive to Prescriptive Analytics

On the Insight Agent page, there is an **"AI Copilot"** button.  
Behind this button, a tiny Python ML model (linear regression with scikit-learn) runs three layers of analytics:

1. **Diagnostic:**  
   - Finds the weakest mill (yield, downtime), the lowest-OTIF customer, and the weakest-margin region over recent periods.

2. **Predictive:**  
   - Trains a simple time-series trend model to forecast fleet yield (next 7 days), OTIF (next ~30 days), and gross margin (next 3 months).

3. **Prescriptive:**  
   - Converts these patterns into a short list of next actions for operations, supply chain, and finance.

This is a proof-of-concept showing how a real AI model could be wired into PanPac's BI stack to move from descriptive dashboards to prescriptive recommendations.

![alt text](image-14.png)
![alt text](image-15.png)
![alt text](image-16.png)

FOR A MORE DETAILED AND COMPLETE README, PLEASE SEE BELOW


````markdown
# PanPac BI Copilot – DuckDB + Python + AI Insight Agent

A portfolio project that simulates a **Senior BI Analyst – Business Intelligence** role for a forestry company like **Pan Pac**.

The app:

- Builds a **semantic BI model** on top of a synthetic forestry dataset (operations, supply chain, finance).
- Serves 3 interactive **Python dashboards** (Streamlit + Plotly).
- Includes an **Insight Agent** for daily KPI briefings.
- Adds an **AI Copilot button** that runs **diagnostic, predictive, and prescriptive** analytics using a tiny scikit-learn model.

---

## 1. Tech Stack

- **Data store:** DuckDB (`panpac.duckdb`)
- **Data generation:** Python + pandas (synthetic PanPac-like dataset)
- **Semantic model:** Star schemas + views on DuckDB
- **Dashboards:** Streamlit + Plotly (pure Python)
- **AI / ML:** scikit-learn (LinearRegression) + rule-based prescriptive logic

---

## 2. Business Context

The project is designed around a job description similar to:

> *Senior Business Analyst – Business Intelligence at Pan Pac*  
> – Own BI roadmap, deliver trusted insights, build semantic models, define KPIs, and enable self-service analytics across operations, supply chain, and finance.

Data simulates a forestry company that:

- Grows, mills, and ships radiata products
- Runs mills and ports in New Zealand
- Sells to domestic and export customers
- Monitors sustainability, yield, OTIF, and margins

---

## 3. Data & Semantic Model

### 3.1 Domains

- **Operations:** mill production, yield, downtime, energy use  
- **Supply Chain:** shipments, OTIF (On-Time-In-Full), lead time  
- **Finance:** revenue, costs, gross margin, EBITDA margin  

### 3.2 Dimensions

- `Dim_Date` – standard calendar
- `Dim_Site` – forests, mills, ports
- `Dim_Product` – logs, timber, pulp, grades
- `Dim_Customer` – domestic vs export customers
- `Dim_Region` – NZ regions + export markets

### 3.3 Facts

- `Fact_Production` (day–site–product)
- `Fact_Shipment` (shipment order)
- `Fact_Finance` (month–product–region)

### 3.4 Semantic Views

- `vw_production` – joins production to date/site/product, adds `yield_pct`
- `vw_shipments` – joins shipments to date/customer/site, adds `otif_flag` and lead time
- `vw_finance` – joins finance to product/region, adds gross & EBITDA margins

Architecture sketch:

```text
Dim_Date   Dim_Site   Dim_Product   Dim_Customer   Dim_Region
   \          |           |              |              |
    \         |           |              |              |
  Fact_Production    Fact_Shipment     Fact_Finance
         \                |                /
          \               |               /
             DuckDB semantic views (vw_production / vw_shipments / vw_finance)
                               |
                         Streamlit app
````

---

## 4. Dashboards (Python / Streamlit)

Run the app:

```bash
pip install -r requirements.txt

# 1. Generate synthetic data + DuckDB (if you don't commit them)
python scripts/generate_data.py
python scripts/load_to_duckdb.py

# 2. Run BI app
streamlit run app/dashboard_app.py
```

The app exposes 4 pages:

### 4.1 Operations – Mill Performance & Yield

* KPIs: total output, average yield, average downtime
* Charts:

  * Yield % over time by mill
  * Total output by mill
* Filters: mill, product

*(insert screenshot here)*

### 4.2 Supply Chain – OTIF & Lead Time

* KPIs: OTIF, on-time %, in-full %, average lead time
* Charts:

  * OTIF by customer
  * Lead time distribution
* Filters: customer, product

*(screenshot)*

### 4.3 Finance – Revenue & Margins

* KPIs: total revenue, gross margin %, EBITDA margin %
* Charts:

  * Revenue trend by month
  * Margin by product
* Filters: product, region

*(screenshot)*

### 4.4 Data Explorer

* Simple page to explore raw semantic views: `vw_production`, `vw_shipments`, `vw_finance`.

---

## 5. Insight Agent – Descriptive Analytics

The **Insight Agent** page generates a **“Daily BI Briefing”**:

* Reads the latest data from DuckDB
* Compares:

  * Operations: today vs 7-day average
  * Supply chain: last 30 days vs previous 30 days
  * Finance: latest month vs last 3 months
* Outputs a short markdown report, e.g.:

```markdown
1. Operations – Mills & Yield
- Yield is stable around 87.5% vs 7-day average.
- Total output softened to 5,341 m³ (-6.0% vs 7-day average).
- Downtime increased to 1.96 hrs/day (+98.5% vs 7-day average).

2. Supply Chain – OTIF & Lead Time
- OTIF improved to 96.3% (+3.2 pts vs prior 30 days).
- Average lead time improved to 12.9 days (-12.8% vs baseline).

3. Finance – Revenue & Margins
- For December 2025, total revenue is $7.9m.
- Gross margin is stable around 35.7%; EBITDA margin around 26.1%.
```

This mimics how a Senior BI Analyst would brief stakeholders daily.

---

## 6. AI Copilot Button – Diagnostic, Predictive, Prescriptive

On the same page there is an **“AI Copilot”** button.

Under the hood it runs three layers:

### 6.1 Diagnostic (rule + stats)

* Finds:

  * Mill with lowest yield and highest downtime (last 30 days)
  * Customer with weakest OTIF (last 30 days)
  * Region with weakest gross margin (last 6 months)

### 6.2 Predictive (tiny ML model)

Uses **LinearRegression** (scikit-learn) on historical trends to forecast:

* Fleet yield – next 7 days
* Average OTIF – next ~30 days
* Gross margin – next 3 months

### 6.3 Prescriptive (simple rule-based actions)

Converts the patterns into **actionable recommendations**, e.g.:

* Focus maintenance on the weakest mill and top downtime drivers
* Run a cut-off / booking workshop with the lowest-OTIF customer
* Review price / product mix in the weakest-margin region

This is a **POC** of how an AI model could be wired into the BI stack to move from descriptive dashboards to prescriptive recommendations.

---

## 7. How this maps to a Senior BI / DA role

This project demonstrates:

* **Semantic modelling & KPI governance**

  * Star schema design, conformed dimensions, grain & join-key discipline.
* **Modern analytics engineering**

  * DuckDB as a local warehouse; SQL views as a semantic layer.
* **BI product thinking**

  * Clear user pages: operations, supply chain, finance, and insight agent.
* **AI-enabled analytics**

  * Small ML model + rule-engine integrated into a BI workflow.
* **Communication**

  * Auto-generated daily briefings and concise, business-friendly insights.

---

## 8. How to run locally

```bash
git clone https://github.com/<your-username>/panpac-bi-copilot.git
cd panpac-bi-copilot

pip install -r requirements.txt

# Option A – use pre-generated data (if included): just run the app
streamlit run app/dashboard_app.py

# Option B – regenerate everything from scratch
python scripts/generate_data.py
python scripts/load_to_duckdb.py
streamlit run app/dashboard_app.py

# Optional: generate a CLI insight report
python agent/insight_agent.py
```

---

## 9. Possible extensions (future work)

* Add anomaly scoring per mill/customer (residual-based models).
* Bring in real NZ forestry / export open data as external benchmarks.
* Add authentication and role-based views (Ops vs Finance).
* Deploy the Streamlit app to a cloud host.

```

