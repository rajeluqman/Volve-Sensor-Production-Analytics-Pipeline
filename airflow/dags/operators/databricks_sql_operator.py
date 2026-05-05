"""
Custom Airflow operators for the Volve pipeline.

DatabricksSQLScriptOperator — runs a local Python script that connects to Databricks SQL Warehouse.
DatabricksSQLQueryOperator  — executes SQL directly against Databricks SQL Warehouse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator


class DatabricksSQLScriptOperator(BaseOperator):
    """
    Runs a Python script as a subprocess.
    The script is expected to connect to Databricks SQL Warehouse using env vars
    (DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN).
    Raises AirflowException on non-zero exit.
    """

    template_fields: Sequence[str] = ("script_path", "script_args")

    def __init__(
        self,
        *,
        script_path: str,
        script_args: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.script_path = script_path
        self.script_args = script_args or []

    def execute(self, context):
        cmd = [sys.executable, self.script_path] + self.script_args
        self.log.info("Running: %s", " ".join(cmd))

        result = subprocess.run(cmd, env={**os.environ})

        if result.returncode != 0:
            raise AirflowException(
                f"Script {self.script_path} exited with code {result.returncode}"
            )


class DatabricksSQLQueryOperator(BaseOperator):
    """
    Executes one or more SQL statements directly against Databricks SQL Warehouse.

    When validation_mode=True, each statement must return rows with columns
    (check_name STRING, passed BOOLEAN). Raises AirflowException on any failed check.
    """

    template_fields: Sequence[str] = ("sql",)

    def __init__(
        self,
        *,
        sql: str | list[str],
        validation_mode: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.sql = [sql] if isinstance(sql, str) else sql
        self.validation_mode = validation_mode

    def execute(self, context):
        from databricks import sql as dbsql
        from dotenv import load_dotenv

        load_dotenv()
        host      = os.environ["DATABRICKS_HOST"].replace("https://", "")
        http_path = os.environ["DATABRICKS_HTTP_PATH"]
        token     = os.environ["DATABRICKS_TOKEN"]

        with dbsql.connect(server_hostname=host, http_path=http_path, access_token=token) as conn:
            for statement in self.sql:
                self.log.info("Executing SQL: %s", statement.strip()[:300])
                with conn.cursor() as cur:
                    cur.execute(statement)
                    if self.validation_mode:
                        rows = cur.fetchall()
                        failed = []
                        for row in rows:
                            check_name, passed = row[0], row[1]
                            if passed:
                                self.log.info("DQ check PASSED: %s", check_name)
                            else:
                                self.log.error("DQ check FAILED: %s", check_name)
                                failed.append(check_name)
                        if failed:
                            raise AirflowException(
                                f"DQ gate blocked — failed checks: {', '.join(failed)}"
                            )
