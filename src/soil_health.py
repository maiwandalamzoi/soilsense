"""
Soil health scorecard.

Produces a 0–100 score from SoilGrids-derived properties using a weighted
sum of normalized sub-scores. Each sub-score is a piecewise linear function
calibrated against commonly cited agronomic thresholds.

References
----------
- FAO (2020). Global assessment of soil pollution.
- FAO (2017). Voluntary Guidelines for Sustainable Soil Management.
- Moebius-Clune et al. (2016). Comprehensive Assessment of Soil Health.
- USDA NRCS soil health indicators.

Scores are indicative and intended for screening-level decisions, not
formal certification. Always validate against field observations.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import SCORECARD_WEIGHTS


@dataclass
class SubScore:
    """Container for a single indicator's contribution to the overall score."""
    name: str
    value: float | None
    unit: str
    score: float          # 0–100
    weight: float
    note: str


@dataclass
class SoilHealthResult:
    overall: float        # 0–100
    subscores: list[SubScore]
    grade: str            # A / B / C / D / F
    summary: str

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "summary": self.summary,
            "subscores": [s.__dict__ for s in self.subscores],
        }


# --------------------------------------------------------------------------- #
# Individual indicator scoring functions
# Each returns (score 0-100, short note explaining the rating)
# --------------------------------------------------------------------------- #
def _score_soc(soc_g_kg: float | None) -> tuple[float, str]:
    """Soil organic carbon (0-5 cm, g/kg). Healthy cropland: >15 g/kg."""
    if soc_g_kg is None:
        return 50.0, "No SOC data — assumed average"
    if soc_g_kg < 5:
        return 20.0, "Very low — high degradation risk"
    if soc_g_kg < 10:
        return 45.0, "Low — below agronomic threshold"
    if soc_g_kg < 15:
        return 65.0, "Moderate — room to improve"
    if soc_g_kg < 25:
        return 85.0, "Good — supports productivity"
    return 95.0, "Excellent — carbon-rich soil"


def _score_ph(ph: float | None) -> tuple[float, str]:
    """pH (H2O). Optimal 6.0–7.5 for most staple crops."""
    if ph is None:
        return 50.0, "No pH data — assumed average"
    if ph < 4.5:
        return 15.0, "Extremely acidic — aluminum toxicity likely"
    if ph < 5.5:
        return 45.0, "Acidic — liming recommended"
    if ph < 6.0:
        return 75.0, "Slightly acidic — acceptable"
    if ph <= 7.5:
        return 95.0, "Optimal range"
    if ph <= 8.2:
        return 70.0, "Slightly alkaline"
    return 40.0, "Alkaline — micronutrient availability reduced"


def _score_nitrogen(n_g_kg: float | None) -> tuple[float, str]:
    """Total nitrogen (g/kg). Healthy: >1.5 g/kg."""
    if n_g_kg is None:
        return 50.0, "No nitrogen data"
    if n_g_kg < 0.5:
        return 25.0, "Very low N — severe deficiency"
    if n_g_kg < 1.0:
        return 50.0, "Low N — fertility constraint"
    if n_g_kg < 1.5:
        return 70.0, "Moderate N"
    if n_g_kg < 3.0:
        return 90.0, "Good N content"
    return 95.0, "N-rich"


def _score_cec(cec: float | None) -> tuple[float, str]:
    """Cation exchange capacity (cmol+/kg). Higher = better nutrient retention."""
    if cec is None:
        return 50.0, "No CEC data"
    if cec < 5:
        return 25.0, "Very low CEC — poor nutrient retention"
    if cec < 10:
        return 50.0, "Low CEC"
    if cec < 15:
        return 70.0, "Moderate CEC"
    if cec < 25:
        return 90.0, "Good CEC"
    return 95.0, "High CEC — excellent nutrient buffer"


def _score_bulk_density(bd: float | None, clay_pct: float | None) -> tuple[float, str]:
    """
    Bulk density (g/cm³). Compaction thresholds depend on texture:
    sandy soils tolerate higher BD than clay soils.
    """
    if bd is None:
        return 50.0, "No bulk density data"

    # Texture-adjusted threshold (USDA NRCS)
    if clay_pct is not None and clay_pct > 40:
        threshold = 1.40
    elif clay_pct is not None and clay_pct > 20:
        threshold = 1.55
    else:
        threshold = 1.65

    if bd < threshold - 0.15:
        return 90.0, "Well-structured, non-compacted"
    if bd < threshold:
        return 70.0, "Acceptable compaction"
    if bd < threshold + 0.1:
        return 40.0, "Compacted — restricts roots"
    return 20.0, "Severely compacted"


def _score_texture(sand_pct: float | None, clay_pct: float | None) -> tuple[float, str]:
    """
    Texture balance. Loam-ish textures (20–35% clay, 30–50% sand) score best
    for general cropping. Extremes on either end are penalized.
    """
    if sand_pct is None or clay_pct is None:
        return 50.0, "No texture data"

    if 20 <= clay_pct <= 35 and 30 <= sand_pct <= 50:
        return 95.0, "Loamy — ideal texture"
    if clay_pct > 55:
        return 45.0, "Heavy clay — drainage issues"
    if sand_pct > 70:
        return 40.0, "Sandy — low water-holding capacity"
    if clay_pct < 10:
        return 55.0, "Low clay — limited nutrient retention"
    return 75.0, "Acceptable texture"


# --------------------------------------------------------------------------- #
# Top-level scoring
# --------------------------------------------------------------------------- #
def compute_soil_health(properties: dict[str, float | None]) -> SoilHealthResult:
    """
    Compute an overall soil health score from SoilGrids properties.

    Parameters
    ----------
    properties : dict with keys matching SOIL_PROPERTIES codes
        (soc, phh2o, clay, sand, nitrogen, cec, bdod)

    Returns
    -------
    SoilHealthResult with overall score, letter grade, and per-indicator breakdown.
    """
    sub_funcs = [
        ("soc",      "Soil Organic Carbon", "g/kg",
         lambda: _score_soc(properties.get("soc"))),
        ("phh2o",    "pH", "",
         lambda: _score_ph(properties.get("phh2o"))),
        ("nitrogen", "Total Nitrogen", "g/kg",
         lambda: _score_nitrogen(properties.get("nitrogen"))),
        ("cec",      "Cation Exchange Capacity", "cmol(+)/kg",
         lambda: _score_cec(properties.get("cec"))),
        ("bdod",     "Bulk Density", "g/cm³",
         lambda: _score_bulk_density(properties.get("bdod"), properties.get("clay"))),
        ("texture",  "Texture", "%",
         lambda: _score_texture(properties.get("sand"), properties.get("clay"))),
    ]

    subscores: list[SubScore] = []
    total = 0.0
    for key, label, unit, fn in sub_funcs:
        score, note = fn()
        weight = SCORECARD_WEIGHTS[key]
        total += score * weight

        # Surface the raw value used for the score
        if key == "texture":
            display_val = properties.get("clay")  # show clay as representative
        else:
            display_val = properties.get(key if key != "phh2o" else "phh2o")

        subscores.append(SubScore(
            name=label,
            value=display_val,
            unit=unit,
            score=round(score, 1),
            weight=weight,
            note=note,
        ))

    overall = round(total, 1)
    grade = _assign_grade(overall)
    summary = _build_summary(overall, subscores)

    return SoilHealthResult(
        overall=overall,
        subscores=subscores,
        grade=grade,
        summary=summary,
    )


def _assign_grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _build_summary(overall: float, subscores: list[SubScore]) -> str:
    weakest = min(subscores, key=lambda s: s.score)
    strongest = max(subscores, key=lambda s: s.score)

    if overall >= 75:
        tone = "Soil health is strong overall."
    elif overall >= 55:
        tone = "Soil health is moderate with targeted improvement potential."
    elif overall >= 40:
        tone = "Soil health is constrained — intervention recommended."
    else:
        tone = "Soil health is severely degraded — urgent remediation needed."

    return (
        f"{tone} "
        f"Strongest indicator: {strongest.name} ({strongest.score:.0f}/100). "
        f"Weakest indicator: {weakest.name} ({weakest.score:.0f}/100)."
    )
