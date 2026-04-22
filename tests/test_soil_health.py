"""Tests for the soil health scorecard."""

import pytest

from src.soil_health import compute_soil_health


def test_all_missing_returns_neutral_score():
    result = compute_soil_health({})
    assert 40 <= result.overall <= 60
    assert result.grade in {"C", "D"}


def test_healthy_soil_gets_high_grade():
    ideal = {
        "soc": 28, "phh2o": 6.5, "clay": 28, "sand": 40,
        "nitrogen": 2.5, "cec": 22, "bdod": 1.2,
    }
    result = compute_soil_health(ideal)
    assert result.overall >= 85
    assert result.grade == "A"


def test_degraded_soil_gets_low_grade():
    degraded = {
        "soc": 3, "phh2o": 4.2, "clay": 8, "sand": 85,
        "nitrogen": 0.3, "cec": 3, "bdod": 1.7,
    }
    result = compute_soil_health(degraded)
    assert result.overall <= 40
    assert result.grade in {"D", "F"}


def test_acidic_soil_triggers_ph_warning():
    acidic = {"phh2o": 4.3, "soc": 15, "clay": 30, "sand": 40,
              "nitrogen": 2, "cec": 15, "bdod": 1.3}
    result = compute_soil_health(acidic)
    ph_sub = next(s for s in result.subscores if s.name == "pH")
    assert ph_sub.score < 30
    assert "acid" in ph_sub.note.lower() or "toxic" in ph_sub.note.lower()


def test_weights_sum_to_one():
    from src.config import SCORECARD_WEIGHTS
    assert abs(sum(SCORECARD_WEIGHTS.values()) - 1.0) < 1e-9


def test_subscores_cover_all_weights():
    result = compute_soil_health({"soc": 10})
    # Six indicators should always be returned (matches SCORECARD_WEIGHTS keys)
    assert len(result.subscores) == 6


@pytest.mark.parametrize("ph,expected_range", [
    (4.0, (0, 30)),
    (5.8, (60, 90)),
    (6.8, (90, 100)),
    (8.0, (60, 85)),
    (9.0, (0, 60)),
])
def test_ph_scoring_monotonicity(ph, expected_range):
    result = compute_soil_health({"phh2o": ph})
    ph_sub = next(s for s in result.subscores if s.name == "pH")
    assert expected_range[0] <= ph_sub.score <= expected_range[1]
