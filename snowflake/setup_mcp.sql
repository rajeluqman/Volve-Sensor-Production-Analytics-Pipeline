-- ============================================================
-- Phase 8 — Snowflake MCP Setup
-- Jalankan dalam Snowflake Worksheet (sekali sahaja)
-- ============================================================

-- Step 1: Create database + schema
-- ------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS VOLVE_DB;
CREATE SCHEMA IF NOT EXISTS VOLVE_DB.SERVING;

-- Step 2: Create the MCP server object
-- Tool: SYSTEM_EXECUTE_SQL — allows Claude to run SQL directly
-- ------------------------------------------------------------
USE DATABASE VOLVE_DB;
USE SCHEMA SERVING;

CREATE OR REPLACE MCP SERVER volve_mcp
  FROM SPECIFICATION $$
    tools:
      - title: "Volve SQL Tool"
        name: "volve_sql"
        type: "SYSTEM_EXECUTE_SQL"
        description: "Execute SQL queries against VOLVE_DB for the Volve pipeline serving layer."
        config:
          read_only: false
          query_timeout: 600
          warehouse: "COMPUTE_WH"
  $$;

-- Verify MCP server created
SHOW MCP SERVERS IN SCHEMA VOLVE_DB.SERVING;

-- Step 3: Generate Programmatic Access Token (PAT)
-- IMPORTANT: Copy the token output immediately — ia tidak akan muncul lagi!
-- Ganti <YOUR_SNOWFLAKE_USERNAME> dengan username anda
-- ------------------------------------------------------------
ALTER USER <YOUR_SNOWFLAKE_USERNAME>
  ADD PROGRAMMATIC ACCESS TOKEN volve_mcp_token
  DAYS_TO_EXPIRY = 90;

-- Output akan ada token secret — save dalam .env sebagai SNOWFLAKE_PAT_TOKEN
