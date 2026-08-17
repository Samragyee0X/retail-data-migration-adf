# Automated Retail Sales Data Pipeline

A pipeline that moves retail sales data from a transactional database through bronze, silver, and gold layers, running unattended every night. Built as a data engineering trainee project, with a focus on the kind of patterns real production pipelines actually need — config-driven design, idempotent reruns, and data quality checks that don't just silently pass or fail.

**Stack used :** Azure SQL Database, Azure Data Factory, Azure Data Lake Storage Gen2, Microsoft Fabric (Lakehouse, PySpark notebooks, Data Pipelines, Delta Lake)

## What it does

New sales get generated on a schedule, copied incrementally into a data lake, cleaned and validated, then rolled up into summary tables ready for reporting — all without anyone touching it after the initial setup.

```
Azure SQL (source)
      │
      ▼
Azure Data Factory
  ├─ pl_generate_sales        simulates new daily transactions
  └─ pl_bronze_ingest         config-driven, full + incremental load
        └─ pl_incremental_load   row-count guard, watermark logic
      │
      ▼
ADLS Gen2 — Bronze (raw Parquet, partitioned by load date)
      │
      ▼
Microsoft Fabric Lakehouse
  pl_silver_orchestrate
    ├─ Invoke_Bronze_Ingest     triggers ADF from Fabric
    ├─ Run_Silver_Dimensions
    ├─ Run_Silver_Fact
    └─ Run_Gold
```

Each stage only starts once the one before it has actually succeeded. A failure anywhere stops the chain rather than letting bad or incomplete data flow downstream.

## Data source

Seed data comes from a public Kaggle dataset:(https://www.kaggle.com/datasets/buharishehu/retail-sales-dataset). Only the columns actually needed for this project's schema were kept — the rest was dropped during seeding.

## The source data model

A star schema in Azure SQL: `dim_customer`, `dim_product`, and `dim_store` sit around `f_sls_t`, the fact table. The dimensions are seeded once and rarely change. The fact table grows constantly, via a stored procedure that fires on a schedule — and that difference between static and ever-growing is really what drives every load-strategy decision in this project.

## Bronze — raw landing zone

A `PipelineConfig` table in Azure SQL controls what gets loaded and how, so adding a new source table is a config row, not a pipeline change. Dimension tables get a full overwrite every run since they're small; the fact table uses an incremental load, filtering on a watermark column and only copying what's genuinely new. A row-count check runs before any copy happens at all — if there's nothing new, the pipeline does nothing rather than writing empty files or nudging the watermark forward for no reason. Fact data lands partitioned by load date; dimensions use a flat path, since they get replaced wholesale each time anyway.

## Silver — cleaned and validated

Two notebooks. `nb_silver_dimensions` standardizes customer, product, and store data — splitting names, normalizing phone numbers, deduplicating — and overwrites in full each run. `nb_silver_fact` checks every sale against all three dimension tables before letting it through; anything that doesn't match a real customer, product, or store gets set aside in a quarantine table instead of being dropped or silently waved through. Loads are append-only, gated by a transaction ID check, so rerunning the notebook never creates duplicates.

## Gold — business-ready aggregates

Four tables, each fully rebuilt from silver on every run rather than appended to: `gold_sales_by_product`, `gold_sales_by_customer`, `gold_sales_by_store`, and `gold_daily_summary` for overall daily KPIs. These keep their business keys instead of getting flattened into one wide table, which matters if this ever gets connected to Power BI — a proper star schema lets relationships get built against it directly, instead of every table carrying duplicated dimension attributes.

## Automation

| Trigger | Schedule | Purpose |
|---|---|---|
| ADF `pl_generate_sales` | Every 2 hours, 1:30 AM–11:30 PM | Simulates new sales through the day |
| Fabric `pl_silver_orchestrate` | Daily, 12:30 AM | Runs the full ingest → silver → gold chain |

There's a deliberate hour of buffer between ADF's last generation run and Fabric's pipeline start, so nothing's being written while the pipeline is mid-run.

Samragi Dhakal — Data Engineering Project
