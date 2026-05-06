"""
Pytest configuration for Volve pipeline tests.

Markers:
  integration  — requires live Databricks + Snowflake credentials (skipped in CI without env vars)
"""

import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require live Databricks/Snowflake connections "
        "(skipped when DATABRICKS_TOKEN or SNOWFLAKE_PASSWORD env vars are absent)",
    )


@pytest.fixture(scope="session")
def databricks_env():
    """Skip if Databricks credentials are not present."""
    token = os.environ.get("DATABRICKS_TOKEN")
    host = os.environ.get("DATABRICKS_HOST")
    http_path = os.environ.get("DATABRICKS_HTTP_PATH")
    if not all([token, host, http_path]):
        pytest.skip("Databricks credentials not set — skipping integration test")
    return {
        "host": host.replace("https://", ""),
        "http_path": http_path,
        "token": token,
    }


@pytest.fixture(scope="session")
def snowflake_env():
    """Skip if Snowflake credentials are not present."""
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        pytest.skip(f"Snowflake credentials missing ({', '.join(missing)}) — skipping integration test")
    return {k: os.environ[k] for k in required}
