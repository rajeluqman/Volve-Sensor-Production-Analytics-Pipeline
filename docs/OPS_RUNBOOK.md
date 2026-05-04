# OPS_RUNBOOK.md — Operations Runbook
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. Monitoring Endpoints

| Service | URL/Command |
|---------|-------------|
| Airflow UI | http://localhost:8080 |
| NiFi UI | https://localhost:8443/nifi |
| Databricks | https://community.cloud.databricks.com |
| DQ Results | SELECT * FROM silver.dq_results WHERE run_date = CURRENT_DATE |

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

---

## 4. Backfill Procedure

```bash
# Step 1: Clear Bronze partition
# In Databricks: spark.sql("DELETE FROM bronze.raw_production WHERE DATEPRD='2014-06-15'")

# Step 2: Trigger with date param
airflow dags trigger volve_daily_pipeline --conf '{"execution_date": "2014-06-15"}'

# Step 3: Verify
# Snowflake: SELECT * FROM silver.dq_results WHERE run_date = '2014-06-15'
```

---

## 5. Codespaces Session Checklist

### Start of Session
```bash
docker ps                         # Check running containers
export $(cat .env | xargs)        # Load env vars
databricks clusters list          # Check Databricks
```

### End of Session
```bash
docker stop $(docker ps -q)       # Stop all containers
# Stop Databricks cluster from UI (save credit)
# Update PROJECT_STATUS.md
```

---

## 6. Daily Ops Checklist

```
☐ Airflow: volve_daily_pipeline SUCCESS semalam?
☐ DQ: Pass rate > 95%?
☐ Quarantine: < 5% rows quarantined?
☐ Databricks cluster auto-terminated?
☐ Snowflake Gold data updated?
```

---

*Document Owner: Data Engineering Team*
