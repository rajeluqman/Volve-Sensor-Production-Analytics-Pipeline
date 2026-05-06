# OPS_RUNBOOK.md — Operations Runbook
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.1 | **Last Updated:** 2026-05-06

---

## 1. Monitoring Endpoints

| Service | URL/Command |
|---------|-------------|
| Airflow UI | http://localhost:8080 |
| NiFi UI | https://localhost:8443/nifi |
| Databricks | https://dbc-6cebbe0d-a59e.cloud.databricks.com |
| Snowflake | https://ke65194.ap-southeast-5.aws.snowflakecomputing.com |
| DQ Results | SELECT * FROM claudecatalog.silver.dq_results WHERE run_date = CURRENT_DATE |

---

## 2. Alert SLAs

| Severity | Channel | Response |
|----------|---------|----------|
| CRITICAL | PagerDuty | 15 minit |
| HIGH | Slack + Email | 1 jam |
| MEDIUM | Email | Hari bekerja |

---

## 3. Playbooks

### SCENARIO 1: Glue Job FAILED
```bash
# Check error
# AWS Console → Glue → Jobs → [job] → Runs → Error

# Fix: S3 file missing
aws s3 ls s3://volve-landing/production/

# Fix: Restart NiFi
docker restart nifi-container

# Rerun
airflow tasks clear volve_daily_pipeline -t run_glue_bronze_production --yes
```

### SCENARIO 2: Databricks Job FAILED
```bash
# Check Databricks UI → Jobs → Latest Run → Error

# Fix: Cluster terminated (most common)
databricks clusters start --cluster-id $DATABRICKS_CLUSTER_ID

# Fix: OOM
# Add in notebook: spark.conf.set("spark.sql.shuffle.partitions", "8")
```

### SCENARIO 3: DQ CRITICAL Fail
```sql
SELECT expectation_type, column_name, observed_value, rows_affected
FROM silver.dq_results
WHERE run_date = CURRENT_DATE AND severity = 'CRITICAL' AND success = FALSE;
```

### SCENARIO 4: NiFi Not Running
```bash
docker ps -a | grep nifi
docker start nifi-container
# Kalau container hilang:
docker run -d --name nifi-container -p 8443:8443 \
  -e SINGLE_USER_CREDENTIALS_USERNAME=admin \
  -e SINGLE_USER_CREDENTIALS_PASSWORD=adminpassword123 \
  apache/nifi:1.23.2
```

### SCENARIO 5: Airflow Not Running
```bash
docker-compose -f infrastructure/docker-compose.yml restart airflow-scheduler airflow-webserver
airflow dags trigger volve_daily_pipeline
```

### SCENARIO 6: Snowflake Load FAILED
```bash
# Check error log
python snowflake/run_snowflake.py --only load 2>&1 | tail -30

# Most common causes:
# (a) SNOWFLAKE_PASSWORD not set in .env
export $(grep -v '^#' .env | xargs)

# (b) Warehouse suspended — auto-resumes on first query, but can force:
# Snowflake UI → Admin → Warehouses → COMPUTE_WH → Resume

# (c) Table schema mismatch — drop and recreate staging tables
python snowflake/run_snowflake.py --only setup
python snowflake/run_snowflake.py --only load

# Verify row count after reload
# Snowflake Worksheet:
# SELECT COUNT(*) FROM VOLVE_DB.SERVING.production_daily;  -- expect ~4,967
```

### SCENARIO 7: Snowflake View Returns 0 Rows
```sql
-- Check staging table has data first
SELECT COUNT(*) FROM VOLVE_DB.SERVING.production_daily;

-- Inspect view definition
SHOW VIEWS IN SCHEMA VOLVE_DB.SERVING;
SELECT GET_DDL('VIEW', 'VOLVE_DB.SERVING.VW_DAILY_PRODUCTION_KPIS');

-- Recreate all 5 views
-- (run from local machine with .env loaded)
-- python snowflake/run_snowflake.py --only views
```

### SCENARIO 8: Snowflake PAT Token Expired
```sql
-- PAT token (volve_mcp_token) is valid for 90 days from 2026-05-05.
-- If expired, regenerate in Snowflake Worksheet:
ALTER USER RAJEMANG SET PASSWORD = '<new_password>';  -- or regenerate PAT via UI

-- Update .env:
-- SNOWFLAKE_PASSWORD=<new_password>
-- SNOWFLAKE_PAT_TOKEN=<new_token>

-- Re-run MCP setup if needed:
-- snowflake/setup_mcp.sql (run in Snowflake Worksheet)
```

---

## 4. Backfill Procedure

```bash
# Step 1: Clear Bronze partition (Databricks Worksheet / notebook)
# DELETE FROM claudecatalog.bronze.raw_production WHERE date_year = 2014;

# Step 2: Re-run Bronze → Silver → Gold scripts
python bronze/run_bronze.py
python silver/run_silver.py
python gold/run_gold.py

# Step 3: Reload Snowflake serving layer
python snowflake/run_snowflake.py --only load

# Step 4: Verify row counts
# Databricks: SELECT COUNT(*) FROM claudecatalog.gold.production_daily;
# Snowflake:  SELECT COUNT(*) FROM VOLVE_DB.SERVING.production_daily;
```

### Snowflake Serving — Reload Only (no Databricks re-run)
```bash
# Truncate + reload from existing Gold tables:
python snowflake/run_snowflake.py --only load

# Verify 5 BI views still return data:
python snowflake/run_snowflake.py --only views
```

---

## 5. Snowflake Serving Layer Reference

| Item | Value |
|------|-------|
| Account | `ke65194.ap-southeast-5.aws` |
| User | `RAJEMANG` |
| Database | `VOLVE_DB` |
| Schema | `SERVING` |
| Warehouse | `COMPUTE_WH` |
| MCP Server | `volve_mcp` |
| PAT Token Name | `volve_mcp_token` (expires 2026-08-03) |

### Staging Tables
| Table | Source | Rows |
|-------|--------|------|
| `VOLVE_DB.SERVING.production_daily` | `gold.production_daily` | ~4,967 |
| `VOLVE_DB.SERVING.ml_predictions` | `gold.ml_predictions` | Populated after Airflow Task 9 |

### BI Views
| View | Purpose |
|------|---------|
| `vw_daily_production_kpis` | Ops KPIs per well/date |
| `vw_anomaly_alerts` | Anomaly flags + CRITICAL/HIGH/MEDIUM severity |
| `vw_production_trends` | Monthly aggregates per well |
| `vw_ml_predictions` | ML actual vs predicted + TRUE_POS/FALSE_POS labels |
| `vw_well_comparison` | Cross-well KPI per year |

### Run Scripts
```bash
python snowflake/run_snowflake.py               # Full: setup + load + views
python snowflake/run_snowflake.py --only setup  # Create DB/schema/tables only
python snowflake/run_snowflake.py --only load   # Truncate + reload from Gold
python snowflake/run_snowflake.py --only views  # Recreate 5 BI views
```

---

## 6. Codespaces Session Checklist

### Start of Session
```bash
docker ps                         # Check running containers
export $(grep -v '^#' .env | xargs)   # Load env vars
databricks clusters list          # Check Databricks
```

### End of Session
```bash
docker stop $(docker ps -q)       # Stop all containers
# Stop Databricks cluster from UI (save credit)
# Update PROJECT_STATUS.md
```

---

## 7. Daily Ops Checklist

```
☐ Airflow: volve_daily_pipeline SUCCESS semalam?
☐ DQ: Pass rate > 95%?  (claudecatalog.silver.dq_results)
☐ Quarantine: < 5% rows quarantined?
☐ Databricks cluster auto-terminated?
☐ Snowflake serving layer updated?  (VOLVE_DB.SERVING.production_daily row count unchanged)
☐ Unit tests green?  (pytest tests/unit/ -v)
☐ Integration smoke tests green (kalau credentials available)?
```

---

*Document Owner: Data Engineering Team*
