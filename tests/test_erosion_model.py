"""Tests for the RUSLE erosion model."""

import pytest

from src.erosion_model import (
    P_FACTOR_PRESETS,
    compute_c_factor,
    compute_k_factor,
    compute_ls_factor,
    compute_r_factor,
    estimate_rusle_point,
)


def test_r_factor_increases_with_rainfall():
    assert compute_r_factor(100) < compute_r_factor(500) < compute_r_factor(1500)


def test_r_factor_zero_rainfall():
    assert compute_r_factor(0) == 0
    assert compute_r_factor(-10) == 0


def test_k_factor_bounded():
    # Typical K values fall roughly between 0.01 and 0.09 SI
    k = compute_k_factor(sand_pct=40, silt_pct=35, clay_pct=25, soc_g_kg=12)
    assert 0 < k < 0.15


def test_ls_factor_increases_with_slope():
    assert compute_ls_factor(1) < compute_ls_factor(5) < compute_ls_factor(15)


def test_c_factor_from_ndvi_monotonic():
    # Higher NDVI → lower C-factor (more protective cover)
    assert compute_c_factor(ndvi=0.2) > compute_c_factor(ndvi=0.5) > compute_c_factor(ndvi=0.8)


def test_c_factor_lookup_fallback():
    assert compute_c_factor(land_cover_class=40) == 0.28  # cropland
    assert compute_c_factor(land_cover_class=10) < 0.01   # tree cover


def test_practice_reduces_loss():
    base = estimate_rusle_point(
        annual_rainfall_mm=900, sand_pct=40, silt_pct=35, clay_pct=25,
        soc_g_kg=10, slope_pct=10, ndvi=0.4, practice="No conservation practice",
    )
    terraced = estimate_rusle_point(
        annual_rainfall_mm=900, sand_pct=40, silt_pct=35, clay_pct=25,
        soc_g_kg=10, slope_pct=10, ndvi=0.4, practice="Terracing",
    )
    assert terraced.soil_loss_t_ha_yr < base.soil_loss_t_ha_yr


def test_all_practices_defined():
    for practice in P_FACTOR_PRESETS:
        e = estimate_rusle_point(
            annual_rainfall_mm=800, sand_pct=40, silt_pct=35, clay_pct=25,
            soc_g_kg=10, slope_pct=5, ndvi=0.4, practice=practice,
        )
        assert e.soil_loss_t_ha_yr >= 0


@pytest.mark.parametrize("slope,expected_class", [
    (0, "Very Low"),
    (30, "Very High"),   # steep + no practice + moderate rainfall
])
def test_risk_classification_extremes(slope, expected_class):
    e = estimate_rusle_point(
        annual_rainfall_mm=1200, sand_pct=30, silt_pct=30, clay_pct=40,
        soc_g_kg=5, slope_pct=slope, ndvi=0.2,
        practice="No conservation practice",
    )
    if slope == 0:
        assert e.risk_class in {"Very Low", "Low"}
    else:
        assert e.risk_class in {"High", "Very High"}
