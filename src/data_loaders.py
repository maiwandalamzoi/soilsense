"""
Data loaders for SoilSense.

Responsibilities
----------------
1. Authenticate with Google Earth Engine using a service account stored
   in Streamlit secrets (works locally via .streamlit/secrets.toml and
   on Streamlit Cloud via the Secrets UI).
2. Fetch point-based soil properties from the SoilGrids 2.0 REST API.
3. Load administrative boundaries for the focus countries.
4. Fetch NDVI time series and rainfall from GEE for a given AOI.

All network calls are wrapped in @st.cache_data with a reasonable TTL so
repeated dashboard interactions stay snappy on Streamlit Cloud.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
import streamlit as st

from src.config import (
    BOUNDARIES_DIR,
    FOCUS_COUNTRIES,
    GEE_COLLECTIONS,
    NDVI_SCALE,
    SOILGRIDS_BASE_URL,
    SOIL_PROPERTIES,
)

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Google Earth Engine initialization
# --------------------------------------------------------------------------- #
_GEE_READY = False


def init_earth_engine() -> bool:
    """
    Initialize Earth Engine using a service account from Streamlit secrets.

    Returns True on success, False if credentials are missing or invalid.
    Failure is non-fatal: the app falls back to SoilGrids-only mode and
    pre-computed sample rasters in data/sample/.
    """
    global _GEE_READY
    if _GEE_READY:
        return True

    try:
        import ee  # imported lazily so the app can boot even if ee install failed
    except ImportError:
        log.warning("earthengine-api not installed; GEE features disabled")
        return False

    try:
        sa_email = st.secrets.get("GEE_SERVICE_ACCOUNT_EMAIL")
        sa_json = st.secrets.get("GEE_SERVICE_ACCOUNT_JSON")
        if not sa_email or not sa_json:
            log.info("GEE secrets not configured; skipping EE init")
            return False

        credentials = ee.ServiceAccountCredentials(
            email=sa_email,
            key_data=sa_json,
        )
        ee.Initialize(credentials=credentials, opt_url="https://earthengine-highvolume.googleapis.com")
        _GEE_READY = True
        log.info("Earth Engine initialized successfully")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Earth Engine init failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# SoilGrids REST API
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def fetch_soilgrids_point(lon: float, lat: float) -> dict[str, float | None]:
    """
    Fetch the full set of configured soil properties at a single point.

    The SoilGrids API returns nested JSON with mean values at several depth
    intervals and uncertainty layers. We pull the 0–5 cm mean for each
    configured property and convert from packed integer to display units.

    Returns a flat dict: {property_code: value_in_display_units or None}
    """
    params = {
        "lon": lon,
        "lat": lat,
        "property": list({p["layer"] for p in SOIL_PROPERTIES.values()}),
        "depth": "0-5cm",
        "value": "mean",
    }

    try:
        resp = requests.get(SOILGRIDS_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.error("SoilGrids request failed: %s", exc)
        return {k: None for k in SOIL_PROPERTIES}

    out: dict[str, float | None] = {}
    layers = {layer["name"]: layer for layer in payload.get("properties", {}).get("layers", [])}

    for code, meta in SOIL_PROPERTIES.items():
        layer = layers.get(meta["layer"])
        if not layer:
            out[code] = None
            continue
        try:
            # Structure: layer["depths"][0]["values"]["mean"]
            depth_entry = next(
                d for d in layer["depths"] if d["label"] == meta["depth"]
            )
            raw = depth_entry["values"].get("mean")
            out[code] = None if raw is None else raw * meta["conversion"]
        except (StopIteration, KeyError, TypeError):
            out[code] = None

    return out


def fetch_soilgrids_grid(
    bounds: tuple[float, float, float, float],
    n: int = 8,
) -> pd.DataFrame:
    """
    Build a coarse grid of soil property samples over a bounding box.

    Used for the regional overview. n×n points. For Kenya-scale AOIs an 8×8
    grid gives ~64 API calls — tolerable with caching, and more than enough
    resolution for a dashboard summary. Not suitable for pixel-level analysis;
    use GEE for that.
    """
    import numpy as np

    minx, miny, maxx, maxy = bounds
    xs = np.linspace(minx, maxx, n)
    ys = np.linspace(miny, maxy, n)

    rows = []
    for x in xs:
        for y in ys:
            props = fetch_soilgrids_point(float(x), float(y))
            rows.append({"lon": x, "lat": y, **props})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Admin boundaries
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def load_country_boundary(country_name: str) -> gpd.GeoDataFrame | None:
    """
    Load a country boundary from the bundled boundaries folder.

    We ship simplified GeoJSON for each FOCUS_COUNTRIES entry (generated
    offline from GADM / Natural Earth — see notebooks/prepare_boundaries.ipynb).
    Falls back to Natural Earth low-res if a local file is missing.
    """
    if country_name not in FOCUS_COUNTRIES:
        return None

    iso3 = FOCUS_COUNTRIES[country_name]["iso3"]
    path = BOUNDARIES_DIR / f"{iso3}.geojson"
    if path.exists():
        return gpd.read_file(path)

    # Fallback: Natural Earth via geopandas' built-in (deprecated but works offline if cached)
    try:
        url = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
        world = gpd.read_file(url)
        match = world[world["ISO_A3"] == iso3]
        if match.empty:
            return None
        return match
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load boundary for %s: %s", country_name, exc)
        return None


# --------------------------------------------------------------------------- #
# NDVI time series via GEE
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_ndvi_timeseries(
    geometry_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Fetch mean NDVI over a polygon for each 16-day MODIS composite.

    Parameters
    ----------
    geometry_geojson : GeoJSON-like mapping (e.g. from shapely's __geo_interface__)
    start_date, end_date : ISO date strings

    Returns an empty DataFrame if GEE is unavailable — the UI handles this.
    """
    if not init_earth_engine():
        return pd.DataFrame(columns=["date", "ndvi"])

    import ee

    try:
        aoi = ee.Geometry(geometry_geojson)
        collection = (
            ee.ImageCollection(GEE_COLLECTIONS["ndvi_modis"])
            .filterDate(start_date, end_date)
            .filterBounds(aoi)
            .select("NDVI")
        )

        def _reduce(img: "ee.Image") -> "ee.Feature":
            mean = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=250,
                maxPixels=1e9,
            ).get("NDVI")
            return ee.Feature(None, {"date": img.date().format("YYYY-MM-dd"), "ndvi": mean})

        fc = collection.map(_reduce).filter(ee.Filter.notNull(["ndvi"]))
        records = fc.getInfo().get("features", [])
        if not records:
            return pd.DataFrame(columns=["date", "ndvi"])

        df = pd.DataFrame([r["properties"] for r in records])
        df["date"] = pd.to_datetime(df["date"])
        df["ndvi"] = df["ndvi"] * NDVI_SCALE
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception as exc:  # noqa: BLE001
        log.error("NDVI fetch failed: %s", exc)
        return pd.DataFrame(columns=["date", "ndvi"])


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_precipitation_annual(
    geometry_geojson: dict[str, Any],
    year: int,
) -> float | None:
    """Fetch total annual precipitation (mm) from CHIRPS over an AOI."""
    if not init_earth_engine():
        return None

    import ee

    try:
        aoi = ee.Geometry(geometry_geojson)
        img = (
            ee.ImageCollection(GEE_COLLECTIONS["precip_chirps"])
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .sum()
        )
        result = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=5000,
            maxPixels=1e9,
        ).getInfo()
        return result.get("precipitation")
    except Exception as exc:  # noqa: BLE001
        log.error("Precipitation fetch failed: %s", exc)
        return None
