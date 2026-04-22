"""
Degradation risk classifier.

A Random Forest model that predicts the probability a given location is at
elevated risk of land degradation, using features that are all obtainable
from free global sources:

    - Soil organic carbon (SoilGrids)
    - pH (SoilGrids)
    - Clay %, Sand % (SoilGrids)
    - Mean annual rainfall (CHIRPS)
    - Slope (SRTM)
    - NDVI long-term mean (MODIS)
    - NDVI trend slope (MODIS) — a standard LDN proxy
    - Land cover class (ESA WorldCover)

Label strategy
--------------
For the portfolio demo we generate **synthetic-but-agronomically-plausible**
labels using a rule-based "teacher" function, then train an RF on that.
This is deliberately transparent: the training notebook documents the
teacher function, and we report train/test metrics on held-out synthetic
data. In production you would replace labels with:
    - LADA-L (Land Degradation Assessment in Drylands) polygons
    - ESA CCI land-cover change between two epochs
    - Trends.Earth SDG 15.3.1 sub-indicator outputs
    - In-situ survey data from FAO/UNCCD partners

We ship a pre-trained model in models/degradation_rf.joblib so the app
works out of the box. See notebooks/02_train_degradation_model.ipynb for
full reproducibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import MODELS_DIR

log = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "soc", "phh2o", "clay", "sand", "nitrogen", "cec", "bdod",
    "rainfall_mm", "slope_pct", "ndvi_mean", "ndvi_trend",
]

MODEL_PATH = MODELS_DIR / "degradation_rf.joblib"


@dataclass
class DegradationPrediction:
    probability: float        # 0–1, probability of 'degraded' class
    risk_label: str           # Low / Moderate / High / Severe
    top_drivers: list[tuple[str, float]]  # (feature, contribution)
    confidence: str           # qualitative statement


# --------------------------------------------------------------------------- #
# Teacher function — synthesizes labels for training
# --------------------------------------------------------------------------- #
def _teacher_label(row: pd.Series) -> int:
    """
    Rule-of-thumb label (0 = not degraded, 1 = degraded).

    The rules encode well-established degradation signals:
      - Declining NDVI trend is a direct LDN indicator
      - Very low SOC + low rainfall + bare cover → dryland degradation
      - Cropland on steep slopes with low residue cover → erosion-driven loss
    """
    score = 0.0
    if row["ndvi_trend"] < -0.003:
        score += 2.5
    if row["soc"] < 8:
        score += 1.5
    if row["ndvi_mean"] < 0.3:
        score += 1.0
    if row["slope_pct"] > 8 and row["soc"] < 12:
        score += 1.0
    if row["rainfall_mm"] < 600 and row["ndvi_mean"] < 0.4:
        score += 1.0
    if row["phh2o"] < 5.0 or row["phh2o"] > 8.5:
        score += 0.5
    if row["bdod"] > 1.55:
        score += 0.5
    return int(score >= 2.5)


def generate_synthetic_training_set(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Produce a synthetic training dataset for the classifier demo."""
    rng = np.random.default_rng(seed)

    df = pd.DataFrame({
        "soc":         rng.gamma(3.0, 3.5, n).clip(0.5, 45),
        "phh2o":       rng.normal(6.3, 0.9, n).clip(3.8, 9.2),
        "clay":        rng.beta(2, 4, n) * 70,
        "sand":        rng.beta(3, 3, n) * 80,
        "nitrogen":    rng.gamma(2.0, 0.6, n).clip(0.1, 5),
        "cec":         rng.gamma(2.5, 5.0, n).clip(1, 50),
        "bdod":        rng.normal(1.35, 0.15, n).clip(0.9, 1.8),
        "rainfall_mm": rng.gamma(2.5, 350, n).clip(150, 2500),
        "slope_pct":   rng.gamma(1.5, 3.0, n).clip(0, 45),
        "ndvi_mean":   rng.beta(3, 3, n).clip(0.05, 0.9),
        "ndvi_trend":  rng.normal(0.0, 0.004, n),
    })
    df["label"] = df.apply(_teacher_label, axis=1)
    return df


# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #
def train_and_save_model(out_path: Path = MODEL_PATH) -> dict[str, float]:
    """
    Train the Random Forest on synthetic data and save to disk.

    Returns a dict of evaluation metrics on a held-out split.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score, f1_score, roc_auc_score,
    )
    from sklearn.model_selection import train_test_split

    df = generate_synthetic_training_set()
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1":       float(f1_score(y_test, y_pred)),
        "roc_auc":  float(roc_auc_score(y_test, y_proba)),
        "n_train":  int(len(X_train)),
        "n_test":   int(len(X_test)),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "metrics": metrics}, out_path)
    log.info("Saved degradation model to %s with metrics %s", out_path, metrics)
    return metrics


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #
_model_cache: dict | None = None


def _load_model() -> dict | None:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    if not MODEL_PATH.exists():
        log.warning("No trained model at %s; train via notebook or call train_and_save_model()", MODEL_PATH)
        return None
    _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


def predict_degradation(features: dict[str, float | None]) -> DegradationPrediction:
    """
    Predict degradation probability for a single location.

    Falls back to a rule-based estimate if the trained model isn't available
    (e.g. first run before training). Missing features are imputed with
    column medians from the training distribution.
    """
    bundle = _load_model()

    # Impute missing values with reasonable defaults
    imputed = {col: features.get(col) for col in FEATURE_COLUMNS}
    defaults = {
        "soc": 10, "phh2o": 6.3, "clay": 25, "sand": 40, "nitrogen": 1.2,
        "cec": 12, "bdod": 1.35, "rainfall_mm": 800, "slope_pct": 3,
        "ndvi_mean": 0.45, "ndvi_trend": 0.0,
    }
    for k, v in defaults.items():
        if imputed[k] is None:
            imputed[k] = v

    if bundle is None:
        # Rule-based fallback — uses the teacher function directly
        row = pd.Series(imputed)
        label = _teacher_label(row)
        proba = 0.75 if label == 1 else 0.25
        drivers = _rule_based_drivers(row)
        return DegradationPrediction(
            probability=proba,
            risk_label=_risk_label(proba),
            top_drivers=drivers,
            confidence="Heuristic (model not yet trained)",
        )

    model = bundle["model"]
    X = pd.DataFrame([imputed])[bundle["features"]]
    proba = float(model.predict_proba(X)[0, 1])

    # Feature contributions via permutation around this sample
    importances = _local_contributions(model, X.iloc[0], bundle["features"])
    top = sorted(importances.items(), key=lambda kv: -abs(kv[1]))[:3]

    return DegradationPrediction(
        probability=proba,
        risk_label=_risk_label(proba),
        top_drivers=top,
        confidence=f"RF model (ROC-AUC={bundle['metrics']['roc_auc']:.2f})",
    )


def _risk_label(p: float) -> str:
    if p < 0.25:
        return "Low"
    if p < 0.5:
        return "Moderate"
    if p < 0.75:
        return "High"
    return "Severe"


def _local_contributions(
    model, sample: pd.Series, feature_names: list[str],
) -> dict[str, float]:
    """
    Lightweight local feature attribution: for each feature, shift it to its
    training-set median and measure the change in predicted probability.
    Not as rigorous as SHAP but keeps the dependency footprint small for
    Streamlit Cloud deployment.
    """
    medians = {
        "soc": 10, "phh2o": 6.3, "clay": 25, "sand": 40, "nitrogen": 1.2,
        "cec": 12, "bdod": 1.35, "rainfall_mm": 800, "slope_pct": 3,
        "ndvi_mean": 0.45, "ndvi_trend": 0.0,
    }
    base = float(model.predict_proba(pd.DataFrame([sample]))[0, 1])
    out = {}
    for f in feature_names:
        perturbed = sample.copy()
        perturbed[f] = medians.get(f, sample[f])
        p = float(model.predict_proba(pd.DataFrame([perturbed]))[0, 1])
        out[f] = base - p  # positive = this feature's current value increases risk
    return out


def _rule_based_drivers(row: pd.Series) -> list[tuple[str, float]]:
    """Top drivers for the heuristic fallback path."""
    drivers = []
    if row["ndvi_trend"] < -0.003:
        drivers.append(("ndvi_trend", 0.3))
    if row["soc"] < 8:
        drivers.append(("soc", 0.25))
    if row["slope_pct"] > 8:
        drivers.append(("slope_pct", 0.15))
    if row["rainfall_mm"] < 600:
        drivers.append(("rainfall_mm", 0.15))
    return drivers[:3] or [("ndvi_mean", 0.1)]
