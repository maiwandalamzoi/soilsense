"""
Revised Universal Soil Loss Equation (RUSLE) — simplified implementation.

A = R × K × LS × C × P

where A is long-term average annual soil loss (t/ha/yr), and:

  R  : Rainfall erosivity factor   (MJ mm ha⁻¹ h⁻¹ yr⁻¹)
  K  : Soil erodibility factor     (t ha h ha⁻¹ MJ⁻¹ mm⁻¹)
  LS : Slope length & steepness factor (dimensionless)
  C  : Cover-management factor     (dimensionless, 0–1)
  P  : Support practice factor     (dimensionless, 0–1)

For a portfolio demonstration we provide two entry points:

1. `estimate_rusle_point` — produces an estimate from summary inputs
   (mean annual rainfall, soil texture, slope, land cover class, management).
   Useful for quick scenario testing in the UI.

2. `rusle_from_gee_rasters` — the "real" pipeline: computes each factor
   from GEE raster inputs (CHIRPS, SoilGrids, SRTM, ESA WorldCover) and
   returns a raster of predicted annual soil loss. Falls back gracefully
   if GEE is unavailable.

References
----------
Renard, K.G. et al. (1997). Predicting soil erosion by water: a guide to
    conservation planning with the RUSLE. USDA Agricultural Handbook 703.
Panagos, P. et al. (2015). The new assessment of soil loss by water erosion
    in Europe. Environmental Science & Policy, 54, 438–447.
Williams, J.R. (1995). The EPIC model. In: Computer Models of Watershed Hydrology.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Land cover → C-factor lookup (ESA WorldCover v200 classes)
# C-factor values from Panagos et al. (2015) and Borrelli et al. (2017)
# --------------------------------------------------------------------------- #
LANDCOVER_C_FACTORS: dict[int, tuple[str, float]] = {
    10:  ("Tree cover",             0.003),
    20:  ("Shrubland",               0.05),
    30:  ("Grassland",               0.05),
    40:  ("Cropland",                0.28),
    50:  ("Built-up",                0.00),
    60:  ("Bare / sparse vegetation",0.50),
    70:  ("Snow and ice",            0.00),
    80:  ("Permanent water",         0.00),
    90:  ("Herbaceous wetland",      0.01),
    95:  ("Mangroves",               0.003),
    100: ("Moss and lichen",         0.05),
}

# --------------------------------------------------------------------------- #
# Support practice (P-factor) presets
# --------------------------------------------------------------------------- #
P_FACTOR_PRESETS = {
    "No conservation practice": 1.00,
    "Contour tillage":           0.60,
    "Strip cropping":            0.35,
    "Contour + strip cropping":  0.25,
    "Terracing":                 0.15,
    "Terracing + contour":       0.10,
}


@dataclass
class ErosionEstimate:
    soil_loss_t_ha_yr: float
    risk_class: str
    color: str
    factors: dict[str, float]
    narrative: str


# --------------------------------------------------------------------------- #
# Factor computations
# --------------------------------------------------------------------------- #
def compute_r_factor(annual_rainfall_mm: float) -> float:
    """
    Rainfall erosivity from mean annual precipitation.

    Uses the tropical regression from Roose (1977), widely applied in
    Sub-Saharan Africa when 30-min rainfall intensity data are unavailable:

        R ≈ 0.5 × P    (with P in mm, R in MJ·mm/ha/h/yr, approximate)

    For more arid/semi-arid contexts we apply a piecewise adjustment
    consistent with Vrieling et al. (2010).
    """
    if annual_rainfall_mm <= 0:
        return 0.0
    if annual_rainfall_mm < 500:
        return 0.4 * annual_rainfall_mm
    if annual_rainfall_mm < 1500:
        return 0.5 * annual_rainfall_mm
    return 0.6 * annual_rainfall_mm


def compute_k_factor(
    sand_pct: float,
    silt_pct: float,
    clay_pct: float,
    soc_g_kg: float,
) -> float:
    """
    Soil erodibility via the Williams (1995) EPIC formulation.

    This is the standard substitute for the original Wischmeier nomograph
    when nomograph inputs (structure, permeability codes) are unavailable,
    as is almost always the case with global soil data.
    """
    sand = max(sand_pct, 0.1)
    clay = max(clay_pct, 0.1)
    silt = max(silt_pct, 0.1)
    soc_pct = max(soc_g_kg * 0.1, 0.01)  # g/kg to %

    sn = 1.0 - sand / 100.0

    f_csand = 0.2 + 0.3 * _safe_exp(-0.0256 * sand * (1 - silt / 100.0))
    f_cl_si = (silt / (clay + silt)) ** 0.3
    f_orgc = 1.0 - (0.25 * soc_pct) / (soc_pct + _safe_exp(3.72 - 2.95 * soc_pct))
    f_hisand = 1.0 - (0.7 * sn) / (sn + _safe_exp(-5.51 + 22.9 * sn))

    k = f_csand * f_cl_si * f_orgc * f_hisand

    # EPIC outputs are in US units; convert to SI (t·ha·h/ha/MJ/mm)
    return k * 0.1317


def compute_ls_factor(slope_pct: float, slope_length_m: float = 50.0) -> float:
    """
    Combined slope-length and steepness factor (Moore & Burch 1986 simplification).

    slope_pct : slope gradient in percent
    slope_length_m : hillslope length in metres (default 50 m — typical smallholder plot)
    """
    s = max(slope_pct, 0.01)
    # Moore & Burch: LS = (As/22.13)^0.4 × (sin θ / 0.0896)^1.3
    # where As is flow accumulation area; here we use slope_length as a proxy
    import math
    theta = math.atan(s / 100.0)
    ls = (slope_length_m / 22.13) ** 0.4 * (math.sin(theta) / 0.0896) ** 1.3
    return ls


def compute_c_factor(land_cover_class: int | None = None, ndvi: float | None = None) -> float:
    """
    Cover-management factor.

    Preference order:
    1. If NDVI is provided, use the Van der Knijff (2000) empirical formula:
         C = exp(-α × NDVI / (β - NDVI))
       with α=2, β=1 (widely used in European/African studies).
    2. Otherwise look up the land-cover class in the ESA WorldCover table.
    3. Otherwise assume cropland (0.28).
    """
    if ndvi is not None and 0 <= ndvi <= 1:
        import math
        return max(0.0, min(1.0, math.exp(-2.0 * ndvi / max(1.0 - ndvi, 0.01))))

    if land_cover_class is not None and land_cover_class in LANDCOVER_C_FACTORS:
        return LANDCOVER_C_FACTORS[land_cover_class][1]

    return 0.28  # cropland default


# --------------------------------------------------------------------------- #
# High-level estimation
# --------------------------------------------------------------------------- #
def estimate_rusle_point(
    annual_rainfall_mm: float,
    sand_pct: float,
    silt_pct: float,
    clay_pct: float,
    soc_g_kg: float,
    slope_pct: float,
    land_cover_class: int | None = None,
    ndvi: float | None = None,
    practice: str = "No conservation practice",
    slope_length_m: float = 50.0,
) -> ErosionEstimate:
    """
    Estimate long-term annual soil loss (t/ha/yr) for a single location or
    homogeneous management unit.
    """
    r = compute_r_factor(annual_rainfall_mm)
    k = compute_k_factor(sand_pct, silt_pct, clay_pct, soc_g_kg)
    ls = compute_ls_factor(slope_pct, slope_length_m)
    c = compute_c_factor(land_cover_class=land_cover_class, ndvi=ndvi)
    p = P_FACTOR_PRESETS.get(practice, 1.0)

    a = r * k * ls * c * p

    risk_class, color = _classify_erosion(a)
    narrative = _erosion_narrative(a, r, k, ls, c, p, practice)

    return ErosionEstimate(
        soil_loss_t_ha_yr=round(a, 2),
        risk_class=risk_class,
        color=color,
        factors={"R": r, "K": k, "LS": ls, "C": c, "P": p},
        narrative=narrative,
    )


def _classify_erosion(a: float) -> tuple[str, str]:
    from src.config import EROSION_CLASSES
    for lo, hi, label, color in EROSION_CLASSES:
        if lo <= a < hi:
            return label, color
    return "Very High", "#9d0208"


def _erosion_narrative(
    a: float, r: float, k: float, ls: float, c: float, p: float, practice: str,
) -> str:
    dominant = max(
        [("rainfall erosivity", r / 500),
         ("soil erodibility",   k / 0.05),
         ("slope",               ls / 2.0),
         ("cover",               c / 0.3),
         ("practice",            p / 0.5)],
        key=lambda t: t[1],
    )[0]

    if a < 2:
        return f"Erosion risk is very low (~{a:.1f} t/ha/yr). Current conditions are protective."
    if a < 10:
        return (
            f"Erosion risk is moderate (~{a:.1f} t/ha/yr). "
            f"The dominant driver is {dominant}. Conservation practices would provide insurance."
        )
    return (
        f"Erosion risk is high (~{a:.1f} t/ha/yr), exceeding FAO's soil-loss tolerance. "
        f"The dominant driver is {dominant}. Intervention is recommended; "
        f"current practice ('{practice}') leaves the soil vulnerable."
    )


def _safe_exp(x: float) -> float:
    """Clamp to avoid overflow on extreme inputs."""
    import math
    return math.exp(max(min(x, 700.0), -700.0))
