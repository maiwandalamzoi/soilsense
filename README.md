<div align="center">

# 🌱 SoilSense

**A decision-support dashboard for sustainable soil management**

Screening-level soil health, erosion risk, and degradation probability for any point on Earth — built on open remote sensing and FAO guidance.

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Built with Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-enabled-4285F4?logo=google-earth)](https://earthengine.google.com)

**[🚀 Live demo](https://soilsense.streamlit.app)** · **[📖 Methodology](#methodology)** · **[🗺️ Roadmap](#roadmap)**

</div>

---

## Why this exists

Around **33% of the world's soils are already moderately to highly degraded**, and degradation is accelerating — yet most field officers, programme staff, and extension workers still wait weeks for regional soil assessments, or work from coarse national averages. SoilSense makes the first 80% of a soil assessment — the part you'd previously pay a consultant for — available in under a minute, for any point on Earth, using only free and open data.

It's designed for:

- **Agricultural extension officers** who need simple risk maps and practice recommendations for a specific plot or village
- **FAO / NGO programme officers** designing Land Degradation Neutrality (LDN), SLM, or climate-smart agriculture projects
- **Researchers and graduate students** who need reproducible soil screening with exportable data
- **Policy analysts** tracking soil-related SDG 15.3.1 indicators at sub-national scale

Not a replacement for field sampling or full ecosystem assessments — explicitly a screening tool.

---

## Features

### 🗺️ Interactive regional view
Select a country from ten Sub-Saharan African focus countries, click any point, and the dashboard pulls the full soil profile in real time. A country-boundary overlay and editorial-quality cartography (Folium + CartoDB Positron) provide instant spatial context.

### 📊 Soil health scorecard (0–100)
Six agronomic indicators — soil organic carbon, pH, total nitrogen, CEC, bulk density, and texture balance — combined with weights calibrated against FAO and NRCS thresholds. Each indicator is returned with a raw value, sub-score, and plain-language note explaining the rating.

### 🌊 Erosion risk via full RUSLE
The Revised Universal Soil Loss Equation, implemented factor-by-factor: rainfall erosivity from CHIRPS, soil erodibility via the Williams/EPIC formulation, slope-steepness from user input or SRTM, cover-management from MODIS NDVI, and practice from user selection. Results are classified into FAO erosion tiers (Very Low → Very High) and accompanied by a narrative identifying the dominant driver.

### 🤖 ML-based degradation probability
A Random Forest classifier trained on 11 features drawn from SoilGrids, CHIRPS, SRTM, and MODIS, producing a calibrated probability of degradation plus the three features driving the prediction at that specific location. Full training pipeline is reproducible and documented in `notebooks/02_train_degradation_model.ipynb`.

### 📋 FAO-grounded practice recommendations
A rule-based engine maps observed conditions to a shortlist of interventions drawn from the **FAO Voluntary Guidelines for Sustainable Soil Management (VGSSM, 2017)** — cover cropping, contour bunds and terracing, liming, agroforestry, zai pits, rotational grazing, and more — each with rationale, expected time-to-impact, and a citation back to the source guideline or WOCAT technology code.

### 📄 Field-ready exports
One-page PDF reports (ReportLab, print-ready) and tidy CSVs for downstream analysis. The PDF is intentionally austere — tables, not charts — because that's what gets printed and carried into the field.

---

## Screenshots

> Add screenshots here after first deployment. Recommended: overview tab, soil-health breakdown, erosion decomposition, recommendations list, and a PDF report preview. `assets/screenshots/*.png`.

---

## Quick start

### Run locally

```bash
git clone https://github.com/YOUR-USERNAME/soilsense.git
cd soilsense

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

The app will open at `http://localhost:8501`. It works out of the box against the SoilGrids REST API. To enable live NDVI and rainfall from Google Earth Engine, see [Enabling Earth Engine](#enabling-earth-engine) below.

### Optional — retrain the degradation model

A pre-trained model ships in `models/degradation_rf.joblib`. To retrain (for example, after editing the teacher function or replacing labels with real degradation polygons):

```bash
jupyter lab notebooks/02_train_degradation_model.ipynb
```

Or from the command line:

```python
from src.ml_model import train_and_save_model
train_and_save_model()
```

---

## Enabling Earth Engine

NDVI time series and CHIRPS rainfall require a Google Earth Engine service account. The app gracefully falls back to a country-level rainfall climatology and a neutral NDVI prior if GEE is not configured, so you can demo the app immediately without setup — but real remote sensing is what makes it genuinely useful.

1. Create a Google Cloud project and enable the **Earth Engine API**.
2. Create a **service account** in that project and generate a JSON key.
3. Register the service account at [signup.earthengine.google.com/#!/service_accounts](https://signup.earthengine.google.com/#!/service_accounts).
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste:
   ```toml
   GEE_SERVICE_ACCOUNT_EMAIL = "your-sa@your-project.iam.gserviceaccount.com"
   GEE_SERVICE_ACCOUNT_JSON = """
   { ...full JSON key contents... }
   """
   ```
5. Restart Streamlit. The sidebar will show a green indicator for Earth Engine.

On Streamlit Cloud, paste the same values into the app's Secrets UI — no JSON file needed.

---

## Methodology

### Soil health scorecard

```
score = Σᵢ wᵢ · subscoreᵢ(xᵢ)
```

Six sub-scores are computed with piecewise-linear ramps calibrated against published agronomic thresholds (FAO 2017; USDA NRCS soil health indicators; Moebius-Clune et al. 2016). Weights are tuned for smallholder rainfed systems:

| Indicator | Weight | Threshold reference |
|---|---|---|
| Soil organic carbon | 0.30 | >15 g/kg healthy (FAO) |
| pH (H₂O) | 0.15 | 6.0–7.5 optimal |
| Total nitrogen | 0.20 | >1.5 g/kg sufficient |
| CEC | 0.15 | >15 cmol(+)/kg good |
| Bulk density | 0.10 | <1.4–1.65 g/cm³ (texture-adjusted) |
| Texture balance | 0.10 | Loam-ish optimal |

All inputs come from SoilGrids 2.0 at 0–5 cm depth. Modify `src/config.py` to tune weights or thresholds for a different context.

### RUSLE erosion model

```
A = R × K × LS × C × P
```

| Factor | Computation | Source |
|---|---|---|
| R (rainfall erosivity) | Piecewise linear from annual precipitation (Roose 1977; Vrieling 2010) | CHIRPS |
| K (soil erodibility) | Williams (1995) EPIC formulation using sand/silt/clay + SOC | SoilGrids |
| LS (slope length-steepness) | Moore & Burch (1986) | User input / SRTM |
| C (cover management) | Van der Knijff (2000) from NDVI; falls back to ESA WorldCover class lookup | MODIS / ESA WC |
| P (support practice) | User selection from presets based on Panagos et al. (2015) | User input |

Output classes follow FAO (2019) erosion tiers: Very Low (<2 t/ha/yr), Low (2–5), Moderate (5–10), High (10–25), Very High (>25).

### Degradation classifier

A Random Forest (300 trees, max depth 12, class-balanced) on 11 features. For this portfolio demonstration the training labels are produced by a **transparent rule-based teacher function** that encodes well-established degradation signals — declining NDVI trend, low SOC on steep slopes, arid conditions with sparse vegetation, acidic or sodic soils. Full teacher logic is in `src/ml_model.py::_teacher_label`.

**Pre-trained model performance on held-out synthetic data:** accuracy 0.99, F1 0.98, ROC-AUC 0.998. These figures describe how well the model learned the teacher; they are *not* ground-truth performance claims.

**For operational deployment**, replace the synthetic labels with real degradation polygons from:
- [LADA-L](https://www.fao.org/land-water/land/land-governance/land-resources-planning-toolbox/category/details/en/c/1036355/) — Land Degradation Assessment in Drylands
- [Trends.Earth](https://trends.earth) — official SDG 15.3.1 sub-indicator outputs
- [ESA CCI Land Cover](https://www.esa-landcover-cci.org/) — multi-epoch change detection
- In-situ survey data from project M&E

### Recommendation engine

A deterministic, auditable rule engine. Conditions over soil properties + erosion + degradation + rainfall + slope map to a catalog of 12 practices drawn from FAO VGSSM (2017) and the WOCAT SLM technology database. Rules are evaluated in priority order with deduplication. This is intentionally *not* an ML system — at this data volume a learned recommender would be misleading, and transparency matters more than marginal accuracy for decisions that affect livelihoods.

---

## Data sources

| Source | Use | License |
|---|---|---|
| [SoilGrids 2.0](https://soilgrids.org) (ISRIC) | Soil properties at 250 m | CC BY 4.0 |
| [MODIS MOD13Q1](https://lpdaac.usgs.gov/products/mod13q1v061/) | NDVI at 250 m, 16-day | Public domain (NASA) |
| [CHIRPS](https://www.chc.ucsb.edu/data/chirps) | Rainfall at ~5 km, daily | Public |
| [SRTM](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1) | Elevation at 30 m | Public domain |
| [ESA WorldCover v200](https://esa-worldcover.org) | Land cover at 10 m (2021) | CC BY 4.0 |
| [GADM](https://gadm.org) / [Natural Earth](https://www.naturalearthdata.com) | Administrative boundaries | Various free |

---

## Architecture

```
┌──────────────────────────────┐
│      Streamlit UI (app.py)   │   Multi-tab layout, custom editorial CSS
└──────────┬───────────────────┘
           │
   ┌───────┴───────┐
   │  src/         │
   ├───────────────┤
   │ data_loaders  │  → SoilGrids REST + GEE service-account auth
   │ soil_health   │  → Weighted scorecard (pure function)
   │ erosion_model │  → RUSLE, factor by factor
   │ ml_model      │  → RF inference + local feature attribution
   │ recommendations│ → Rule engine over FAO VGSSM catalog
   │ reporting     │  → ReportLab PDF + tidy CSV
   └───────────────┘
```

Everything below the UI layer is plain Python with no Streamlit dependency, which keeps the domain logic unit-testable and reusable outside the dashboard.

---

## Project structure

```
soilsense/
├── app.py                         # Streamlit entry point
├── src/
│   ├── config.py                  # Countries, thresholds, weights, GEE collections
│   ├── data_loaders.py            # SoilGrids + Earth Engine fetchers (cached)
│   ├── soil_health.py             # 0-100 scorecard
│   ├── erosion_model.py           # Full RUSLE implementation
│   ├── ml_model.py                # RF training + inference
│   ├── recommendations.py         # FAO VGSSM rule engine
│   └── reporting.py               # PDF + CSV export
├── notebooks/
│   └── 02_train_degradation_model.ipynb
├── models/
│   └── degradation_rf.joblib      # Pre-trained model (ships in repo)
├── data/
│   ├── boundaries/                # Country GeoJSONs (auto-downloaded on first run)
│   └── sample/                    # Sample rasters for offline demo
├── tests/
│   ├── test_soil_health.py
│   └── test_erosion_model.py
├── assets/
├── .streamlit/
│   ├── config.toml                # Theme
│   └── secrets.toml.example       # Template for GEE credentials
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

---

## Testing

```bash
pip install pytest
pytest tests/ -v
```

Tests cover the pure-function domain modules (scorecard, RUSLE factors, monotonicity checks, edge cases). Network-dependent loaders are not tested in CI — mock them if you extend the suite.

---

## Limitations and caveats

Stating these clearly is part of the point. A useful screening tool is honest about what it is and isn't.

- **Screening, not diagnosis.** Global 250 m soil products have substantial uncertainty at the plot level. Always validate with field sampling before programming decisions.
- **RUSLE assumptions.** RUSLE predicts long-term average sheet-and-rill erosion on single hillslopes; it does not capture gully erosion, landslides, or event-based losses. The LS factor here uses a default 50 m hillslope length — site-specific values should be provided where available.
- **Synthetic ML labels.** The shipped Random Forest is trained on labels produced by a rule-based teacher, not observed degradation. This is transparently documented and the notebook shows exactly how to retrain on real labels.
- **Climate fallbacks.** When Earth Engine is unavailable, rainfall uses a country-level climatology and NDVI uses a neutral prior. The sidebar makes this status explicit.
- **Single depth.** All soil properties are read at 0–5 cm. Subsoil properties matter for many management questions; this is a known extension.
- **Slope from user input.** The current version takes slope as an input rather than deriving it from SRTM within the app. Raster-based slope computation is on the roadmap.

---

## Roadmap

- [ ] Time-slider for multi-year comparisons and SDG 15.3.1 indicator computation
- [ ] Upload-your-own-shapefile mode (analyze a specific farm or programme area)
- [ ] Pixel-scale erosion and degradation rasters (currently point-based)
- [ ] Side-by-side region comparison mode
- [ ] Model cards for each ML component following Google's Model Cards framework
- [ ] French and Swahili translations (FAO priority languages)
- [ ] Subsoil properties (5–15 cm, 15–30 cm, 30–60 cm depths from SoilGrids)
- [ ] Docker image and reproducible environment via devcontainer
- [ ] Retraining on real LDN polygons (Trends.Earth integration)

Contributions welcome — please open an issue first to discuss larger changes.

---

## Citation

If you use SoilSense in a publication, programme design, or consultancy report, please cite:

```bibtex
@software{soilsense_2026,
  author = {YOUR NAME},
  title  = {SoilSense: A Decision-Support Dashboard for Sustainable Soil Management},
  year   = {2026},
  url    = {https://github.com/YOUR-USERNAME/soilsense}
}
```

Please also cite the underlying data products (SoilGrids, MODIS, CHIRPS, SRTM, ESA WorldCover) and methods (Renard et al. 1997 for RUSLE; Williams 1995 for EPIC K-factor).

---

## License

MIT — see [LICENSE](LICENSE). Data from SoilGrids, ESA WorldCover, and similar products retain their own licenses; this project's license applies only to the code.

---

## Acknowledgements

- **ISRIC — World Soil Information** for the SoilGrids data product and REST API
- **Google Earth Engine** for making petabyte-scale remote sensing accessible
- **FAO Global Soil Partnership** for the Voluntary Guidelines for Sustainable Soil Management
- **CHG, UCSB** for CHIRPS rainfall
- **WOCAT** for the open SLM technology database

Built with Streamlit, GeoPandas, scikit-learn, Plotly, Folium, and ReportLab.

---

<div align="center">
<sub>
Built by a soil management specialist who codes — not the other way around.
</sub>
</div>
