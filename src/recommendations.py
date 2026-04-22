"""
Management practice recommendation engine.

Maps observed soil conditions, erosion risk, and degradation prediction
to a shortlist of interventions drawn from:

  - FAO (2017) Voluntary Guidelines for Sustainable Soil Management (VGSSM)
  - FAO (2019) Soil erosion: the greatest challenge for sustainable soil management
  - WOCAT (World Overview of Conservation Approaches and Technologies) database

Each rule has:
  * a condition over inputs
  * one or more recommended practices
  * a short rationale citing the relevant FAO guidance
  * an expected time-to-impact (short/medium/long)

The engine is intentionally simple — rule-based, transparent, auditable.
A learned recommender would be misleading at this data volume and would
undermine the trust smallholders and extension officers need.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Recommendation:
    title: str
    category: str
    rationale: str
    time_to_impact: str          # "Short (<1 yr)" / "Medium (1-3 yr)" / "Long (3+ yr)"
    priority: int                # 1 (highest) – 3 (lowest)
    fao_reference: str
    tags: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Practice catalog
# --------------------------------------------------------------------------- #
# Defined once, selected by the rule engine. Easier to maintain than
# inline strings inside conditions.
PRACTICES = {
    "cover_crops": Recommendation(
        title="Introduce cover crops in fallow periods",
        category="Soil organic matter",
        rationale=(
            "Leguminous cover crops (e.g. mucuna, lablab, sunn hemp) fix "
            "nitrogen, protect bare soil from erosive rainfall, and add "
            "3–8 t/ha of biomass that raises SOC over successive seasons."
        ),
        time_to_impact="Medium (1–3 yr)",
        priority=1,
        fao_reference="FAO VGSSM §3.2.1; FAO (2019) Ch. 5",
        tags=["low_soc", "erosion", "cropland"],
    ),
    "residue_retention": Recommendation(
        title="Retain crop residues (conservation agriculture)",
        category="Soil organic matter",
        rationale=(
            "Leaving ≥30% of residues on the surface reduces raindrop impact, "
            "slows runoff, and recycles nutrients. Pair with reduced tillage "
            "for compounded gains."
        ),
        time_to_impact="Short (<1 yr)",
        priority=1,
        fao_reference="FAO VGSSM §3.2.2",
        tags=["low_soc", "erosion", "compaction"],
    ),
    "liming": Recommendation(
        title="Apply agricultural lime",
        category="Chemical amendment",
        rationale=(
            "Acidic soils (pH < 5.5) suffer aluminum and manganese toxicity "
            "and poor phosphorus availability. 1–3 t/ha of lime raises pH "
            "toward the optimal 6.0–7.0 range within a season."
        ),
        time_to_impact="Short (<1 yr)",
        priority=1,
        fao_reference="FAO VGSSM §3.3.1",
        tags=["acidic"],
    ),
    "gypsum": Recommendation(
        title="Apply gypsum to alkaline / sodic soils",
        category="Chemical amendment",
        rationale=(
            "Gypsum (CaSO₄·2H₂O) displaces sodium from the cation exchange "
            "complex, improving structure and reducing dispersion in alkaline soils."
        ),
        time_to_impact="Medium (1–3 yr)",
        priority=2,
        fao_reference="FAO VGSSM §3.3.2",
        tags=["alkaline"],
    ),
    "terracing": Recommendation(
        title="Construct bench terraces or fanya juu",
        category="Erosion control",
        rationale=(
            "On slopes >15% terracing is the most effective single intervention, "
            "cutting soil loss by 70–90%. Fanya juu is labor-light and widely "
            "adopted across East African highlands."
        ),
        time_to_impact="Long (3+ yr to fully stabilize)",
        priority=1,
        fao_reference="FAO (2019) Ch. 6; WOCAT T_KEN004",
        tags=["steep_slope", "high_erosion"],
    ),
    "contour_bunds": Recommendation(
        title="Contour bunds or stone lines",
        category="Erosion control",
        rationale=(
            "On moderate slopes (3–15%), contour bunds intercept runoff, "
            "encourage infiltration, and trap sediment. Low-cost and reversible."
        ),
        time_to_impact="Short (<1 yr)",
        priority=2,
        fao_reference="FAO (2019) Ch. 6",
        tags=["moderate_slope", "high_erosion"],
    ),
    "agroforestry": Recommendation(
        title="Integrate nitrogen-fixing trees (agroforestry)",
        category="Biological intervention",
        rationale=(
            "Species like Faidherbia albida, Gliricidia, and Leucaena deliver "
            "10–80 kg N/ha/yr via litterfall, diversify income, and buffer microclimate. "
            "Especially effective in drylands where rainfall < 800 mm."
        ),
        time_to_impact="Long (3+ yr)",
        priority=2,
        fao_reference="FAO VGSSM §3.2.3; World Agroforestry Centre",
        tags=["low_soc", "low_rainfall", "low_nitrogen"],
    ),
    "manure": Recommendation(
        title="Apply well-composted farmyard manure",
        category="Organic amendment",
        rationale=(
            "5–10 t/ha of composted manure adds N, P, K, and micronutrients; "
            "raises CEC and water-holding capacity. Prefer composted over fresh "
            "to reduce nitrogen loss and weed seed load."
        ),
        time_to_impact="Short (<1 yr)",
        priority=1,
        fao_reference="FAO VGSSM §3.2.2",
        tags=["low_soc", "low_nitrogen", "low_cec"],
    ),
    "reduced_tillage": Recommendation(
        title="Shift to reduced or zero tillage",
        category="Physical management",
        rationale=(
            "Minimizing tillage preserves aggregate structure, reduces SOC "
            "oxidation, and cuts diesel/labor costs. Combine with cover crops "
            "and residue retention for the full conservation agriculture package."
        ),
        time_to_impact="Medium (1–3 yr)",
        priority=2,
        fao_reference="FAO VGSSM §3.2.2",
        tags=["compaction", "low_soc"],
    ),
    "crop_rotation": Recommendation(
        title="Diversify rotations with legumes",
        category="Biological intervention",
        rationale=(
            "Rotations including legumes (beans, cowpea, groundnut, pigeonpea) "
            "break pest cycles and contribute 30–120 kg N/ha/yr. Monoculture "
            "systems degrade SOC 2–3× faster than diversified rotations."
        ),
        time_to_impact="Medium (1–3 yr)",
        priority=1,
        fao_reference="FAO VGSSM §3.2.1",
        tags=["low_nitrogen", "cropland"],
    ),
    "water_harvesting": Recommendation(
        title="Install in-field water harvesting (zaï pits, half-moons)",
        category="Water management",
        rationale=(
            "In rainfall < 600 mm, micro-catchments concentrate water and "
            "nutrients around the plant, doubling yields on degraded Sahelian "
            "soils. Proven across Burkina Faso, Niger, and northern Ethiopia."
        ),
        time_to_impact="Short (<1 yr)",
        priority=1,
        fao_reference="FAO (2019) Ch. 6; WOCAT T_BFA002",
        tags=["low_rainfall", "degraded"],
    ),
    "grazing_mgmt": Recommendation(
        title="Rotational grazing / stocking rate control",
        category="Biological intervention",
        rationale=(
            "Overgrazing is a primary driver of rangeland degradation. "
            "Rotational systems with rest periods allow vegetation recovery, "
            "maintain ground cover, and sustain forage productivity."
        ),
        time_to_impact="Medium (1–3 yr)",
        priority=2,
        fao_reference="FAO VGSSM §3.4",
        tags=["grassland", "degraded"],
    ),
}


# --------------------------------------------------------------------------- #
# Rule engine
# --------------------------------------------------------------------------- #
def recommend_practices(
    soil_props: dict[str, float | None],
    erosion_t_ha_yr: float | None,
    degradation_probability: float | None,
    slope_pct: float | None,
    annual_rainfall_mm: float | None,
    land_cover: str | None = "cropland",
) -> list[Recommendation]:
    """
    Return a prioritized list of recommended practices.

    Rules are evaluated in order of priority; duplicates are suppressed so
    a single practice never appears twice even if multiple rules match.
    """
    selected: dict[str, Recommendation] = {}

    def _add(key: str) -> None:
        if key in PRACTICES and key not in selected:
            selected[key] = PRACTICES[key]

    soc = soil_props.get("soc")
    ph = soil_props.get("phh2o")
    n = soil_props.get("nitrogen")
    cec = soil_props.get("cec")
    bd = soil_props.get("bdod")

    # --- Erosion ----------------------------------------------------------- #
    if erosion_t_ha_yr is not None and erosion_t_ha_yr >= 10:
        if slope_pct is not None and slope_pct > 15:
            _add("terracing")
        else:
            _add("contour_bunds")
        _add("residue_retention")
        _add("cover_crops")

    # --- Acidity / alkalinity --------------------------------------------- #
    if ph is not None:
        if ph < 5.5:
            _add("liming")
        elif ph > 8.3:
            _add("gypsum")

    # --- Low SOC ---------------------------------------------------------- #
    if soc is not None and soc < 12:
        _add("manure")
        _add("cover_crops")
        _add("residue_retention")
        if annual_rainfall_mm is not None and annual_rainfall_mm < 800:
            _add("agroforestry")

    # --- Low N ------------------------------------------------------------ #
    if n is not None and n < 1.2:
        _add("crop_rotation")
        _add("agroforestry")

    # --- Compaction ------------------------------------------------------- #
    if bd is not None and bd > 1.55:
        _add("reduced_tillage")
        _add("residue_retention")

    # --- Low CEC (nutrient retention) ------------------------------------ #
    if cec is not None and cec < 8:
        _add("manure")

    # --- Arid conditions -------------------------------------------------- #
    if annual_rainfall_mm is not None and annual_rainfall_mm < 600:
        _add("water_harvesting")
        _add("agroforestry")

    # --- High predicted degradation probability --------------------------- #
    if degradation_probability is not None and degradation_probability >= 0.5:
        _add("cover_crops")
        _add("agroforestry")
        if land_cover and "grass" in land_cover.lower():
            _add("grazing_mgmt")

    # --- Safety net: always give at least two ----------------------------- #
    if not selected:
        _add("cover_crops")
        _add("residue_retention")

    return sorted(selected.values(), key=lambda r: r.priority)
