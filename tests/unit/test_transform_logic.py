"""
Unit tests for Volve pipeline transform logic.

These tests mirror the SQL business rules defined in CLAUDE.md and implemented
in silver/silver_production.py and gold/gold_production_daily.py. No database
connection required — each function is a pure Python equivalent of the SQL CASE.
"""

import re
import pytest


# ---------------------------------------------------------------------------
# Pure Python implementations (mirrors the SQL CASE expressions)
# ---------------------------------------------------------------------------

def compute_water_cut(oil_vol, water_vol):
    """BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100; NULL if denom=0."""
    oil = oil_vol or 0.0
    wat = water_vol or 0.0
    total = oil + wat
    if total <= 0:
        return None
    return wat / total * 100.0


def compute_gor(gas_vol, oil_vol):
    """BORE_GAS_VOL / BORE_OIL_VOL; NULL if oil=0 or NULL."""
    if not oil_vol or oil_vol <= 0:
        return None
    return (gas_vol or 0.0) / oil_vol


def flag_zero_prod_uptime(oil_vol, on_stream_hrs):
    """TRUE when well is on-stream but reports zero oil production."""
    if oil_vol is None or on_stream_hrs is None:
        return False
    return oil_vol == 0 and on_stream_hrs > 0


def flag_pressure_valid(pressure):
    """TRUE when 0 <= pressure <= 10000 psi. NULL pressure → FALSE."""
    if pressure is None:
        return False
    return 0 <= pressure <= 10000


def flag_anomaly_pressure(pressure_delta_24h):
    """TRUE when |pressure delta| > 500 psi in 24 hours."""
    if pressure_delta_24h is None:
        return False
    return pressure_delta_24h > 500


def flag_water_cut_spike(water_cut, lag_water_cut):
    """TRUE when today > 80% AND yesterday < 60% (step-change detection)."""
    if water_cut is None or lag_water_cut is None:
        return False
    return water_cut > 80 and lag_water_cut < 60


def flag_gor_anomaly(gor, baseline_gor):
    """TRUE when current GOR exceeds 3× well baseline average."""
    if gor is None or baseline_gor is None or baseline_gor == 0:
        return False
    return gor > baseline_gor * 3


def extract_well_id(well_bore_code):
    """REGEXP_EXTRACT(WELL_BORE_CODE, 'F-[0-9]+') — returns first match or None."""
    if not well_bore_code:
        return None
    match = re.search(r"F-[0-9]+", well_bore_code)
    return match.group(0) if match else None


LAS_NULL_VALUE = -999.25


def replace_las_null(value):
    """Replace LAS sentinel value -999.25 with None."""
    if value == LAS_NULL_VALUE:
        return None
    return value


# ---------------------------------------------------------------------------
# Tests — water_cut_pct
# ---------------------------------------------------------------------------

class TestWaterCut:
    def test_typical_case(self):
        result = compute_water_cut(oil_vol=100, water_vol=400)
        assert result == pytest.approx(80.0)

    def test_zero_water(self):
        assert compute_water_cut(oil_vol=500, water_vol=0) == pytest.approx(0.0)

    def test_zero_oil(self):
        # 100% water
        assert compute_water_cut(oil_vol=0, water_vol=200) == pytest.approx(100.0)

    def test_both_zero_returns_none(self):
        assert compute_water_cut(oil_vol=0, water_vol=0) is None

    def test_none_inputs_treated_as_zero(self):
        # None treated as 0; denom = oil(0)+water(200) = 200
        assert compute_water_cut(oil_vol=None, water_vol=200) == pytest.approx(100.0)

    def test_both_none_returns_none(self):
        assert compute_water_cut(oil_vol=None, water_vol=None) is None

    def test_boundary_50_50(self):
        assert compute_water_cut(oil_vol=50, water_vol=50) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Tests — gas_oil_ratio
# ---------------------------------------------------------------------------

class TestGOR:
    def test_typical_case(self):
        assert compute_gor(gas_vol=1000, oil_vol=100) == pytest.approx(10.0)

    def test_zero_oil_returns_none(self):
        assert compute_gor(gas_vol=500, oil_vol=0) is None

    def test_none_oil_returns_none(self):
        assert compute_gor(gas_vol=500, oil_vol=None) is None

    def test_zero_gas_returns_zero(self):
        assert compute_gor(gas_vol=0, oil_vol=100) == pytest.approx(0.0)

    def test_none_gas_treated_as_zero(self):
        assert compute_gor(gas_vol=None, oil_vol=100) == pytest.approx(0.0)

    def test_high_gor(self):
        assert compute_gor(gas_vol=50000, oil_vol=100) == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# Tests — is_zero_prod_uptime flag
# ---------------------------------------------------------------------------

class TestZeroProdUptime:
    def test_zero_oil_with_uptime(self):
        assert flag_zero_prod_uptime(oil_vol=0, on_stream_hrs=12.0) is True

    def test_positive_oil(self):
        assert flag_zero_prod_uptime(oil_vol=100, on_stream_hrs=24.0) is False

    def test_zero_uptime(self):
        assert flag_zero_prod_uptime(oil_vol=0, on_stream_hrs=0) is False

    def test_none_oil(self):
        assert flag_zero_prod_uptime(oil_vol=None, on_stream_hrs=12.0) is False

    def test_none_uptime(self):
        assert flag_zero_prod_uptime(oil_vol=0, on_stream_hrs=None) is False


# ---------------------------------------------------------------------------
# Tests — is_pressure_valid flag
# ---------------------------------------------------------------------------

class TestPressureValid:
    def test_valid_mid_range(self):
        assert flag_pressure_valid(5000) is True

    def test_zero_boundary(self):
        assert flag_pressure_valid(0) is True

    def test_max_boundary(self):
        assert flag_pressure_valid(10000) is True

    def test_negative_pressure(self):
        assert flag_pressure_valid(-1) is False

    def test_above_max(self):
        assert flag_pressure_valid(10001) is False

    def test_none_pressure(self):
        assert flag_pressure_valid(None) is False


# ---------------------------------------------------------------------------
# Tests — anomaly flags (Gold layer)
# ---------------------------------------------------------------------------

class TestAnomalyPressure:
    def test_exceeds_threshold(self):
        assert flag_anomaly_pressure(501) is True

    def test_exactly_threshold_not_anomaly(self):
        # Business rule: strictly > 500
        assert flag_anomaly_pressure(500) is False

    def test_below_threshold(self):
        assert flag_anomaly_pressure(200) is False

    def test_none_delta(self):
        assert flag_anomaly_pressure(None) is False

    def test_large_spike(self):
        assert flag_anomaly_pressure(1500) is True


class TestWaterCutSpike:
    def test_spike_detected(self):
        assert flag_water_cut_spike(water_cut=85, lag_water_cut=55) is True

    def test_no_spike_both_high(self):
        # Both high → not a spike
        assert flag_water_cut_spike(water_cut=85, lag_water_cut=82) is False

    def test_no_spike_both_low(self):
        assert flag_water_cut_spike(water_cut=40, lag_water_cut=35) is False

    def test_exact_boundary_today(self):
        # Exactly 80 → not > 80 → no spike
        assert flag_water_cut_spike(water_cut=80, lag_water_cut=55) is False

    def test_exact_boundary_yesterday(self):
        # Yesterday exactly 60 → not < 60 → no spike
        assert flag_water_cut_spike(water_cut=85, lag_water_cut=60) is False

    def test_none_values(self):
        assert flag_water_cut_spike(None, 55) is False
        assert flag_water_cut_spike(85, None) is False


class TestGORAnomalyFlag:
    def test_anomaly_detected(self):
        # GOR = 4 * baseline → anomaly
        assert flag_gor_anomaly(gor=400, baseline_gor=100) is True

    def test_exactly_3x_not_anomaly(self):
        # Strictly > 3× baseline
        assert flag_gor_anomaly(gor=300, baseline_gor=100) is False

    def test_below_threshold(self):
        assert flag_gor_anomaly(gor=150, baseline_gor=100) is False

    def test_zero_baseline(self):
        assert flag_gor_anomaly(gor=300, baseline_gor=0) is False

    def test_none_gor(self):
        assert flag_gor_anomaly(None, baseline_gor=100) is False

    def test_none_baseline(self):
        assert flag_gor_anomaly(gor=300, baseline_gor=None) is False


# ---------------------------------------------------------------------------
# Tests — well_id extraction
# ---------------------------------------------------------------------------

class TestExtractWellId:
    def test_f1(self):
        assert extract_well_id("NO 15/9-F-1 AH") == "F-1"

    def test_f11(self):
        assert extract_well_id("NO 15/9-F-11 H") == "F-11"

    def test_f12(self):
        assert extract_well_id("NO 15/9-F-12 AH") == "F-12"

    def test_exact_code(self):
        assert extract_well_id("F-12") == "F-12"

    def test_no_match_returns_none(self):
        assert extract_well_id("UNKNOWN_WELL") is None

    def test_empty_string_returns_none(self):
        assert extract_well_id("") is None

    def test_none_returns_none(self):
        assert extract_well_id(None) is None

    def test_multidigit_well(self):
        assert extract_well_id("NO 15/9-F-123") == "F-123"


# ---------------------------------------------------------------------------
# Tests — LAS null value replacement
# ---------------------------------------------------------------------------

class TestLASNullReplacement:
    def test_sentinel_replaced(self):
        assert replace_las_null(-999.25) is None

    def test_valid_value_unchanged(self):
        assert replace_las_null(1234.5) == 1234.5

    def test_zero_unchanged(self):
        assert replace_las_null(0.0) == 0.0

    def test_none_passthrough(self):
        assert replace_las_null(None) is None

    def test_close_but_not_sentinel(self):
        assert replace_las_null(-999.26) == -999.26
