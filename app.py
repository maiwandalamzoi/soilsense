"""
SoilSense — Streamlit dashboard entry point.

Run locally:
    streamlit run app.py

Deploy on Streamlit Cloud:
    1. Push this repo to GitHub (public)
    2. Sign in at share.streamlit.io
    3. Point it at app.py
    4. Add GEE_SERVICE_ACCOUNT_EMAIL and GEE_SERVICE_ACCOUNT_JSON to Secrets
"""

from __future__ import annotations

from datetime import date, timedelta

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.config import DEFAULT_COUNTRY, FOCUS_COUNTRIES, SOIL_PROPERTIES
from src.data_loaders import (
    fetch_ndvi_timeseries,
    fetch_precipitation_annual,
    fetch_soilgrids_point,
    init_earth_engine,
    load_country_boundary,
)
from src.erosion_model import P_FACTOR_PRESETS, estimate_rusle_point
from src.ml_model import predict_degradation
from src.recommendations import recommend_practices
from src.reporting import build_csv_export, build_pdf_report
from src.soil_health import compute_soil_health

# --------------------------------------------------------------------------- #
# Page config & global styles
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="SoilSense · Soil Management Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "SoilSense is an open-source decision-support dashboard for "
            "sustainable soil management, built on SoilGrids, Google Earth "
            "Engine, and FAO Voluntary Guidelines."
        ),
        "Report a bug": "https://github.com/your-username/soilsense/issues",
    },
)

# Custom CSS — editorial, earthy, restrained
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,600;0,800;1,400&family=Inter:wght@400;500;600&display=swap');

      html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
      }
      h1, h2, h3, h4 {
        font-family: 'Fraunces', serif !important;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: #2D3A1F;
      }
      h1 { font-size: 2.4rem !important; letter-spacing: -0.02em; }
      .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
      .stTabs [data-baseweb="tab"] {
        font-family: 'Fraunces', serif;
        font-size: 1rem;
      }
      .metric-card {
        background: #EFE9DD;
        border-left: 3px solid #A0522D;
        padding: 0.9rem 1.1rem;
        border-radius: 2px;
      }
      .score-hero {
        font-family: 'Fraunces', serif;
        font-size: 3.6rem;
        font-weight: 800;
        line-height: 1;
        color: #A0522D;
      }
      .score-hero-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #6B4A2E;
      }
      .eyebrow {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: #6B4A2E;
        margin-bottom: 0.25rem;
      }
      .divider {
        border-top: 1px solid #D4C9B0;
        margin: 1.5rem 0;
      }
      blockquote {
        border-left: 3px solid #A0522D;
        padding-left: 1rem;
        color: #4A3A2A;
        font-style: italic;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("<div style='font-size:3rem; margin-top:0.4rem;'>🌱</div>", unsafe_allow_html=True)
with col_title:
    st.markdown("<div class='eyebrow'>Decision support · Sustainable soil management</div>",
                unsafe_allow_html=True)
    st.markdown("# SoilSense")
    st.markdown(
        "<p style='color:#4A3A2A; font-size:1.05rem; max-width:70ch;'>"
        "A screening tool for soil health, erosion risk, and degradation "
        "probability — built on open remote sensing and FAO guidance."
        "</p>",
        unsafe_allow_html=True,
    )

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Sidebar — location selection & parameters
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### Location")
    country = st.selectbox(
        "Country",
        list(FOCUS_COUNTRIES.keys()),
        index=list(FOCUS_COUNTRIES.keys()).index(DEFAULT_COUNTRY),
    )
    meta = FOCUS_COUNTRIES[country]

    st.markdown("### Point of interest")
    st.caption("Click the map or enter coordinates. Defaults to country centroid.")

    if "poi_lon" not in st.session_state or st.session_state.get("poi_country") != country:
        st.session_state["poi_lon"] = meta["centroid"][0]
        st.session_state["poi_lat"] = meta["centroid"][1]
        st.session_state["poi_country"] = country

    lon = st.number_input("Longitude", value=float(st.session_state["poi_lon"]),
                          format="%.4f", step=0.01)
    lat = st.number_input("Latitude", value=float(st.session_state["poi_lat"]),
                          format="%.4f", step=0.01)
    st.session_state["poi_lon"] = lon
    st.session_state["poi_lat"] = lat

    st.markdown("### Terrain & management")
    slope_pct = st.slider("Slope (%)", 0.0, 45.0, 4.0, 0.5,
                          help="Field or plot-level slope. Critical driver of erosion.")
    practice = st.selectbox(
        "Conservation practice", list(P_FACTOR_PRESETS.keys()),
        help="Current support practice — RUSLE P-factor.",
    )

    st.markdown("### Data sources")
    ee_ready = init_earth_engine()
    st.markdown(
        f"- SoilGrids 2.0 &nbsp;{'🟢' if True else '🔴'}\n"
        f"- Google Earth Engine &nbsp;{'🟢' if ee_ready else '🟡 offline'}"
    )
    if not ee_ready:
        st.caption(
            "Earth Engine is not initialized. NDVI and rainfall use a "
            "climatology fallback. Configure `GEE_SERVICE_ACCOUNT_*` in "
            "Streamlit secrets to enable live remote sensing."
        )

# --------------------------------------------------------------------------- #
# Data fetching
# --------------------------------------------------------------------------- #
with st.spinner(f"Fetching soil profile at {lat:.3f}°, {lon:.3f}°…"):
    soil_props = fetch_soilgrids_point(lon, lat)

# Rainfall: try GEE for the latest full year; fall back to a regional climatology
rainfall_mm = None
if ee_ready:
    from shapely.geometry import Point
    buffered = Point(lon, lat).buffer(0.1).__geo_interface__
    rainfall_mm = fetch_precipitation_annual(buffered, date.today().year - 1)
if rainfall_mm is None:
    # Climatology fallback by country (rough means, FAO AQUASTAT)
    rainfall_climatology = {
        "Kenya": 630, "Ethiopia": 850, "Uganda": 1180, "Tanzania": 1020,
        "Rwanda": 1200, "Ghana": 1180, "Senegal": 690, "Malawi": 1180,
        "Zambia": 1020, "Burkina Faso": 750,
    }
    rainfall_mm = rainfall_climatology.get(country, 800)

# NDVI time series
ndvi_df = pd.DataFrame()
if ee_ready:
    from shapely.geometry import Point
    buffered = Point(lon, lat).buffer(0.05).__geo_interface__
    start = (date.today() - timedelta(days=365 * 3)).isoformat()
    end = date.today().isoformat()
    ndvi_df = fetch_ndvi_timeseries(buffered, start, end)

ndvi_mean = float(ndvi_df["ndvi"].mean()) if not ndvi_df.empty else 0.45
# Linear trend (per day) as a degradation proxy
ndvi_trend = 0.0
if not ndvi_df.empty and len(ndvi_df) > 6:
    import numpy as np
    x = (ndvi_df["date"] - ndvi_df["date"].min()).dt.days.to_numpy()
    y = ndvi_df["ndvi"].to_numpy()
    if x.std() > 0:
        ndvi_trend = float(np.polyfit(x, y, 1)[0])

# --------------------------------------------------------------------------- #
# Compute
# --------------------------------------------------------------------------- #
health = compute_soil_health(soil_props)

erosion = estimate_rusle_point(
    annual_rainfall_mm=rainfall_mm,
    sand_pct=soil_props.get("sand") or 40,
    silt_pct=max(0, 100 - (soil_props.get("sand") or 40) - (soil_props.get("clay") or 25)),
    clay_pct=soil_props.get("clay") or 25,
    soc_g_kg=soil_props.get("soc") or 10,
    slope_pct=slope_pct,
    ndvi=ndvi_mean,
    practice=practice,
)

degradation = predict_degradation({
    "soc": soil_props.get("soc"),
    "phh2o": soil_props.get("phh2o"),
    "clay": soil_props.get("clay"),
    "sand": soil_props.get("sand"),
    "nitrogen": soil_props.get("nitrogen"),
    "cec": soil_props.get("cec"),
    "bdod": soil_props.get("bdod"),
    "rainfall_mm": rainfall_mm,
    "slope_pct": slope_pct,
    "ndvi_mean": ndvi_mean,
    "ndvi_trend": ndvi_trend,
})

recommendations = recommend_practices(
    soil_props=soil_props,
    erosion_t_ha_yr=erosion.soil_loss_t_ha_yr,
    degradation_probability=degradation.probability,
    slope_pct=slope_pct,
    annual_rainfall_mm=rainfall_mm,
)

# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
tab_map, tab_health, tab_erosion, tab_degradation, tab_recs, tab_export = st.tabs([
    "Overview", "Soil health", "Erosion", "Degradation risk",
    "Recommendations", "Export",
])

# --- Overview tab ------------------------------------------------------ #
with tab_map:
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("### Regional view")
        boundary = load_country_boundary(country)

        m = folium.Map(
            location=[meta["centroid"][1], meta["centroid"][0]],
            zoom_start=meta["zoom"],
            tiles="CartoDB positron",
        )
        if boundary is not None:
            folium.GeoJson(
                boundary.__geo_interface__,
                name=country,
                style_function=lambda _: {
                    "fillColor": "#A0522D", "color": "#4A2E1A",
                    "weight": 1.2, "fillOpacity": 0.08,
                },
            ).add_to(m)

        folium.CircleMarker(
            location=[lat, lon],
            radius=10,
            color="#9d0208",
            fill=True,
            fill_color="#A0522D",
            fill_opacity=0.9,
            popup=f"Analysis point<br>{lat:.4f}°, {lon:.4f}°",
        ).add_to(m)

        st_folium(m, height=480, width=None, returned_objects=[])

    with right:
        st.markdown("### Headline indicators")

        st.markdown(
            f"<div class='eyebrow'>Soil health score</div>"
            f"<div class='score-hero'>{health.overall:.0f}<span style='font-size:1.6rem; color:#6B4A2E;'>/100</span></div>"
            f"<div class='score-hero-sub'>Grade {health.grade}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<br>{health.summary}", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='eyebrow'>Erosion risk</div>"
                f"<div style='font-family:Fraunces,serif; font-size:1.4rem; font-weight:600; color:#2D3A1F;'>"
                f"{erosion.risk_class}</div>"
                f"<div style='color:#6B4A2E;'>{erosion.soil_loss_t_ha_yr} t/ha/yr</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='eyebrow'>Degradation probability</div>"
                f"<div style='font-family:Fraunces,serif; font-size:1.4rem; font-weight:600; color:#2D3A1F;'>"
                f"{degradation.probability*100:.0f}%</div>"
                f"<div style='color:#6B4A2E;'>{degradation.risk_label} risk</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='eyebrow'>Context</div>"
            f"**Mean annual rainfall:** {rainfall_mm:.0f} mm<br>"
            f"**NDVI (3-yr mean):** {ndvi_mean:.2f}<br>"
            f"**Slope:** {slope_pct:.1f}%",
            unsafe_allow_html=True,
        )

# --- Soil health tab --------------------------------------------------- #
with tab_health:
    st.markdown("### Indicator breakdown")
    st.caption(
        "Each indicator contributes to the overall score with the weight "
        "shown. Scoring functions use piecewise-linear ramps calibrated to "
        "FAO and NRCS thresholds."
    )

    sub_df = pd.DataFrame([{
        "Indicator": s.name,
        "Value": s.value,
        "Unit": s.unit,
        "Score": s.score,
        "Weight": s.weight,
        "Note": s.note,
    } for s in health.subscores])

    left, right = st.columns([3, 2], gap="large")

    with left:
        fig = px.bar(
            sub_df, x="Score", y="Indicator", orientation="h",
            color="Score",
            color_continuous_scale=[
                (0, "#9d0208"), (0.4, "#e76f51"),
                (0.55, "#f4a261"), (0.7, "#52b788"), (1, "#2d6a4f"),
            ],
            range_color=(0, 100),
            hover_data={"Value": True, "Unit": True, "Note": True},
        )
        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#FAF7F2",
            plot_bgcolor="#FAF7F2",
            font=dict(family="Inter, sans-serif"),
            yaxis=dict(categoryorder="total ascending"),
            coloraxis_showscale=False,
        )
        fig.update_traces(texttemplate="%{x:.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        for s in health.subscores:
            val_str = "—" if s.value is None else f"{s.value:.2f} {s.unit}".strip()
            st.markdown(
                f"**{s.name}** · {val_str}  \n"
                f"<span style='color:#6B4A2E; font-size:0.9rem;'>{s.note}</span>",
                unsafe_allow_html=True,
            )

    # NDVI chart if available
    if not ndvi_df.empty:
        st.markdown("### NDVI time series")
        st.caption("MODIS 16-day composite. Long-term decline is a standard LDN degradation signal.")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=ndvi_df["date"], y=ndvi_df["ndvi"],
            mode="lines", line=dict(color="#2d6a4f", width=2), name="NDVI",
        ))
        fig2.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#FAF7F2", plot_bgcolor="#FAF7F2",
            font=dict(family="Inter, sans-serif"),
            yaxis=dict(title="NDVI", range=[0, 1]),
        )
        st.plotly_chart(fig2, use_container_width=True)

# --- Erosion tab ------------------------------------------------------- #
with tab_erosion:
    st.markdown("### RUSLE erosion estimate")
    st.markdown(f"<blockquote>{erosion.narrative}</blockquote>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted soil loss", f"{erosion.soil_loss_t_ha_yr} t/ha/yr", erosion.risk_class)
    c2.metric("Rainfall erosivity (R)", f"{erosion.factors['R']:.0f}")
    c3.metric("Slope length-steepness (LS)", f"{erosion.factors['LS']:.2f}")

    st.markdown("#### Factor decomposition")
    st.caption("A = R × K × LS × C × P. Dominant factor shown in the narrative above.")

    factor_df = pd.DataFrame([
        {"Factor": "R — Rainfall erosivity",  "Value": erosion.factors["R"], "Source": "CHIRPS / climatology"},
        {"Factor": "K — Soil erodibility",    "Value": erosion.factors["K"], "Source": "SoilGrids + EPIC"},
        {"Factor": "LS — Slope length/steepness", "Value": erosion.factors["LS"], "Source": "User input / SRTM"},
        {"Factor": "C — Cover management",    "Value": erosion.factors["C"], "Source": "MODIS NDVI"},
        {"Factor": "P — Support practice",    "Value": erosion.factors["P"], "Source": "User selection"},
    ])
    st.dataframe(factor_df, use_container_width=True, hide_index=True)

    st.markdown(
        "<sub>Method: Renard et al. (1997). K-factor via Williams (1995) EPIC formulation. "
        "C-factor from NDVI (Van der Knijff 2000). Tolerable soil loss for tropical soils "
        "is typically 2–11 t/ha/yr (FAO 2019).</sub>",
        unsafe_allow_html=True,
    )

# --- Degradation tab --------------------------------------------------- #
with tab_degradation:
    st.markdown("### Degradation risk (machine learning)")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(
            f"<div class='eyebrow'>Probability</div>"
            f"<div class='score-hero' style='color:#9d0208;'>{degradation.probability*100:.0f}%</div>"
            f"<div class='score-hero-sub'>{degradation.risk_label} risk</div>"
            f"<div style='color:#6B4A2E; margin-top:0.8rem; font-size:0.85rem;'>{degradation.confidence}</div>",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("#### Top drivers at this location")
        st.caption(
            "Local contributions — how much each feature's current value "
            "raises (positive) or lowers (negative) the predicted probability "
            "relative to the median."
        )
        driver_df = pd.DataFrame(
            [{"Feature": f, "Contribution": round(c, 3)} for f, c in degradation.top_drivers]
        )
        if not driver_df.empty:
            fig3 = px.bar(
                driver_df, x="Contribution", y="Feature",
                orientation="h", color="Contribution",
                color_continuous_scale=["#2d6a4f", "#f4a261", "#9d0208"],
            )
            fig3.update_layout(
                height=260, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#FAF7F2", plot_bgcolor="#FAF7F2",
                font=dict(family="Inter, sans-serif"),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig3, use_container_width=True)

    with st.expander("About the model"):
        st.markdown(
            "- **Algorithm:** Random Forest (300 trees, max depth 12, class-balanced)\n"
            "- **Features:** 11 variables from SoilGrids, MODIS, CHIRPS, SRTM\n"
            "- **Training labels:** Synthetic, rule-based *teacher* that encodes "
            "well-established degradation signals (declining NDVI, low SOC, "
            "steep slopes on low-cover land, arid conditions with sparse vegetation)\n"
            "- **Intended use:** Screening. For operational M&E, retrain on "
            "LADA-L polygons, Trends.Earth SDG 15.3.1 outputs, or in-situ survey data.\n"
            "- **Reproducibility:** See `notebooks/02_train_degradation_model.ipynb`."
        )

# --- Recommendations tab ---------------------------------------------- #
with tab_recs:
    st.markdown("### Recommended practices")
    st.caption(
        "Prioritized interventions derived from the scorecard, erosion "
        "estimate, and degradation prediction. Practice descriptions and "
        "references follow the FAO Voluntary Guidelines for Sustainable "
        "Soil Management (2017)."
    )

    for r in recommendations:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"#### {r.title}")
                st.markdown(f"*{r.category} · Priority {r.priority}*")
                st.markdown(r.rationale)
                st.markdown(
                    f"<sub><i>Reference: {r.fao_reference}</i></sub>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div class='metric-card'>"
                    f"<div class='eyebrow'>Time to impact</div>"
                    f"<div style='font-family:Fraunces,serif; font-size:1.05rem; color:#2D3A1F;'>"
                    f"{r.time_to_impact}</div></div>",
                    unsafe_allow_html=True,
                )

# --- Export tab -------------------------------------------------------- #
with tab_export:
    st.markdown("### Export assessment")
    st.caption("One-page PDF for field use, or tidy CSV for downstream analysis.")

    location_label = f"{country} — {lat:.4f}°, {lon:.4f}°"

    pdf_bytes = build_pdf_report(
        location_label=location_label,
        lon=lon, lat=lat,
        health=health,
        erosion=erosion,
        degradation=degradation,
        recommendations=recommendations,
    )

    csv_text = build_csv_export(
        location_label=location_label,
        lon=lon, lat=lat,
        health=health,
        erosion=erosion,
        degradation=degradation,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📄 Download PDF report",
            data=pdf_bytes,
            file_name=f"soilsense_{country.lower()}_{lat:.3f}_{lon:.3f}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "📊 Download CSV",
            data=csv_text,
            file_name=f"soilsense_{country.lower()}_{lat:.3f}_{lon:.3f}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-size:0.8rem; color:#6B4A2E; line-height:1.6;'>"
    "<b>Data:</b> SoilGrids 2.0 © ISRIC · MODIS MOD13Q1 · CHIRPS · SRTM · ESA WorldCover.&nbsp;"
    "<b>Methods:</b> RUSLE (Renard et al. 1997); EPIC K-factor (Williams 1995); "
    "C-factor from NDVI (Van der Knijff 2000); practices per FAO VGSSM (2017). "
    "<br>Screening tool only — validate with field observations before programming decisions.</div>",
    unsafe_allow_html=True,
)
