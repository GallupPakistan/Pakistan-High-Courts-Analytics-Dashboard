# Pakistan High Courts Analytics Dashboard

A Streamlit dashboard for cross-court cause-list analytics across Pakistan's High Courts (Lahore, Sindh, Peshawar, Balochistan, Islamabad) — legal category distribution, crosstab, and temporal trend analysis.

## Features

- **Overview** — KPI summary, filters by Court / Bench-Division / Case Category / Date Range
- **Compare Courts** — side-by-side court comparison
- **Court Details** — per-court drill-down
- **Bench / Division** — bench-type breakdowns
- **Case Categories** — category distribution, "Top Categories at a Glance" (lightbulb visual), Section Citation Coverage gauge, top cited legal sections, category-vs-court crosstab, yearly volume
- **Trends Over Time** — temporal listing trends
- **Workload Analysis** — judge/court workload views
- **Reports** — exportable summaries
- **Data Dictionary** — field/category definitions
- **About** — project info

## Project Structure

```
dashboard - Copy/
├── app.py                     # Entry point
├── requirements.txt
├── components/
│   ├── filters.py
│   ├── top_bar.py
│   ├── sidebar.py
│   ├── kpi_cards.py
│   ├── icons.py
│   └── charts/
│       ├── bar_chart.py
│       ├── sankey_chart.py
│       ├── donut_chart.py
│       ├── trend_line.py
│       ├── map_chart.py
│       ├── lightbulb_chart.py   # Category donut-in-a-lightbulb visual
│       └── gauge_chart.py       # Half-donut coverage gauge
├── views/
│   ├── overview.py
│   ├── court_details.py
│   ├── compare_courts.py
│   ├── bench_division.py
│   ├── workload_analysis.py
│   ├── case_categories.py
│   ├── trends_over_time.py
│   ├── reports.py
│   ├── data_dictionary.py
│   └── about.py
├── styles/
│   ├── theme.py
│   └── dashboard.css
├── utils/
│   ├── data_loader.py
│   ├── formatting.py
│   ├── category_normalizer.py
│   └── bench_type_normalizer.py
└── data/
    └── combined_dashboard_master.parquet
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dashboard runs at `http://localhost:8501`.

## Data

`data/combined_dashboard_master.parquet` — consolidated cause-list records with columns: `Court, Bench_Location, Court_Room, Judge, Bench_Type, Case_No, Case_Year, Case_Category, Case_Stage, Section, Petitioner, Respondent, Petitioner_Advocate, Respondent_Advocate, Hearing_Date, Case_Title`.

## Tech Stack

- [Streamlit](https://streamlit.io/) — app framework
- [Plotly](https://plotly.com/python/) — charts
- [Pandas](https://pandas.pydata.org/) / [PyArrow](https://arrow.apache.org/docs/python/) — data handling
- Custom inline SVG components (lightbulb chart, gauge chart) rendered via `streamlit.components.v1.html`
