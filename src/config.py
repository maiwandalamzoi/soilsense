"""
Configuration and constants for SoilSense.

Central place for AOI defaults, soil property metadata, thresholds,
and file paths. Keeping these here avoids magic numbers across modules.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
MODELS_DIR = ROOT / "models"
ASSETS_DIR = ROOT / "assets"

# --------------------------------------------------------------------------- #
# Global coverage — all continents
# Organised by FAO regional groupings for easy maintenance.
# Fields: iso3 (ISO 3166-1 alpha-3), centroid (lon, lat), zoom (map default)
# --------------------------------------------------------------------------- #
FOCUS_COUNTRIES = {

    # ── SUB-SAHARAN AFRICA ──────────────────────────────────────────────── #
    "Angola":              {"iso3": "AGO", "centroid": (17.8739, -11.2027), "zoom": 5},
    "Benin":               {"iso3": "BEN", "centroid": (2.3158,   9.3077),  "zoom": 7},
    "Botswana":            {"iso3": "BWA", "centroid": (24.6849, -22.3285), "zoom": 6},
    "Burkina Faso":        {"iso3": "BFA", "centroid": (-1.5616,  12.2383), "zoom": 7},
    "Burundi":             {"iso3": "BDI", "centroid": (29.9189,  -3.3731), "zoom": 8},
    "Cameroon":            {"iso3": "CMR", "centroid": (12.3547,   3.8480), "zoom": 6},
    "Chad":                {"iso3": "TCD", "centroid": (18.7322,  15.4542), "zoom": 6},
    "Congo (DRC)":         {"iso3": "COD", "centroid": (23.6560,  -4.0383), "zoom": 5},
    "Côte d'Ivoire":       {"iso3": "CIV", "centroid": (-5.5471,   7.5400), "zoom": 7},
    "Ethiopia":            {"iso3": "ETH", "centroid": (40.4897,   9.1450), "zoom": 6},
    "Ghana":               {"iso3": "GHA", "centroid": (-1.0232,   7.9465), "zoom": 7},
    "Guinea":              {"iso3": "GIN", "centroid": (-11.3412,  11.7402),"zoom": 7},
    "Kenya":               {"iso3": "KEN", "centroid": (37.9062,   0.0236), "zoom": 6},
    "Lesotho":             {"iso3": "LSO", "centroid": (28.2336,  -29.6100),"zoom": 8},
    "Madagascar":          {"iso3": "MDG", "centroid": (46.8691,  -18.7669),"zoom": 6},
    "Malawi":              {"iso3": "MWI", "centroid": (34.3015,  -13.2543),"zoom": 7},
    "Mali":                {"iso3": "MLI", "centroid": (-1.9816,   17.5707),"zoom": 6},
    "Mozambique":          {"iso3": "MOZ", "centroid": (35.5296,  -18.6657),"zoom": 6},
    "Namibia":             {"iso3": "NAM", "centroid": (18.4904,  -22.9576),"zoom": 6},
    "Niger":               {"iso3": "NER", "centroid": (8.0817,   17.6078), "zoom": 6},
    "Nigeria":             {"iso3": "NGA", "centroid": (8.6753,    9.0820), "zoom": 6},
    "Rwanda":              {"iso3": "RWA", "centroid": (29.8739,  -1.9403), "zoom": 8},
    "Senegal":             {"iso3": "SEN", "centroid": (-14.4524,  14.4974),"zoom": 7},
    "Sierra Leone":        {"iso3": "SLE", "centroid": (-11.7799,   8.4606),"zoom": 8},
    "Somalia":             {"iso3": "SOM", "centroid": (45.3438,   5.1521), "zoom": 6},
    "South Africa":        {"iso3": "ZAF", "centroid": (25.0830,  -29.0000),"zoom": 5},
    "South Sudan":         {"iso3": "SSD", "centroid": (31.3070,   7.8626), "zoom": 6},
    "Sudan":               {"iso3": "SDN", "centroid": (30.2176,  12.8628), "zoom": 6},
    "Tanzania":            {"iso3": "TZA", "centroid": (34.8888,  -6.3690), "zoom": 6},
    "Togo":                {"iso3": "TGO", "centroid": (0.8248,    8.6195), "zoom": 7},
    "Uganda":              {"iso3": "UGA", "centroid": (32.2903,   1.3733), "zoom": 7},
    "Zambia":              {"iso3": "ZMB", "centroid": (27.8493,  -13.1339),"zoom": 6},
    "Zimbabwe":            {"iso3": "ZWE", "centroid": (29.1549,  -19.0154),"zoom": 6},

    # ── NORTH AFRICA & MIDDLE EAST ──────────────────────────────────────── #
    "Algeria":             {"iso3": "DZA", "centroid": (1.6596,   28.0339), "zoom": 5},
    "Egypt":               {"iso3": "EGY", "centroid": (30.8025,  26.8206), "zoom": 6},
    "Iraq":                {"iso3": "IRQ", "centroid": (43.6793,  33.2232), "zoom": 6},
    "Jordan":              {"iso3": "JOR", "centroid": (36.2384,  30.5852), "zoom": 7},
    "Lebanon":             {"iso3": "LBN", "centroid": (35.8623,  33.8547), "zoom": 8},
    "Libya":               {"iso3": "LBY", "centroid": (17.2283,  26.3351), "zoom": 6},
    "Morocco":             {"iso3": "MAR", "centroid": (-7.0926,  31.7917), "zoom": 6},
    "Palestine":           {"iso3": "PSE", "centroid": (35.2332,  31.9522), "zoom": 9},
    "Saudi Arabia":        {"iso3": "SAU", "centroid": (45.0792,  23.8859), "zoom": 5},
    "Syria":               {"iso3": "SYR", "centroid": (38.9968,  34.8021), "zoom": 7},
    "Tunisia":             {"iso3": "TUN", "centroid": (9.5375,   33.8869), "zoom": 7},
    "Turkey":              {"iso3": "TUR", "centroid": (35.2433,  38.9637), "zoom": 6},
    "Yemen":               {"iso3": "YEM", "centroid": (47.5769,  15.5527), "zoom": 6},

    # ── ASIA-PACIFIC ────────────────────────────────────────────────────── #
    "Afghanistan":         {"iso3": "AFG", "centroid": (67.7100,  33.9391), "zoom": 6},
    "Australia":           {"iso3": "AUS", "centroid": (133.7751, -25.2744),"zoom": 4},
    "Bangladesh":          {"iso3": "BGD", "centroid": (90.3563,  23.6850), "zoom": 7},
    "Bhutan":              {"iso3": "BTN", "centroid": (90.4336,  27.5142), "zoom": 8},
    "Cambodia":            {"iso3": "KHM", "centroid": (104.9910,  12.5657),"zoom": 7},
    "China":               {"iso3": "CHN", "centroid": (104.1954,  35.8617),"zoom": 4},
    "Fiji":                {"iso3": "FJI", "centroid": (178.0650, -17.7134),"zoom": 8},
    "India":               {"iso3": "IND", "centroid": (78.9629,  20.5937), "zoom": 5},
    "Indonesia":           {"iso3": "IDN", "centroid": (113.9213,  -0.7893),"zoom": 5},
    "Iran":                {"iso3": "IRN", "centroid": (53.6880,  32.4279), "zoom": 5},
    "Japan":               {"iso3": "JPN", "centroid": (138.2529,  36.2048),"zoom": 5},
    "Kazakhstan":          {"iso3": "KAZ", "centroid": (66.9237,  48.0196), "zoom": 5},
    "Kyrgyzstan":          {"iso3": "KGZ", "centroid": (74.7661,  41.2044), "zoom": 7},
    "Laos":                {"iso3": "LAO", "centroid": (102.4955,  19.8563),"zoom": 7},
    "Malaysia":            {"iso3": "MYS", "centroid": (109.6976,   4.2105),"zoom": 6},
    "Mongolia":            {"iso3": "MNG", "centroid": (103.8467,  46.8625),"zoom": 5},
    "Myanmar":             {"iso3": "MMR", "centroid": (95.9560,  21.9162), "zoom": 6},
    "Nepal":               {"iso3": "NPL", "centroid": (84.1240,  28.3949), "zoom": 7},
    "New Zealand":         {"iso3": "NZL", "centroid": (174.8860, -40.9006),"zoom": 5},
    "Pakistan":            {"iso3": "PAK", "centroid": (69.3451,  30.3753), "zoom": 6},
    "Papua New Guinea":    {"iso3": "PNG", "centroid": (143.9555,  -6.3149),"zoom": 6},
    "Philippines":         {"iso3": "PHL", "centroid": (121.7740,  12.8797),"zoom": 6},
    "Solomon Islands":     {"iso3": "SLB", "centroid": (160.1562,  -9.6457),"zoom": 7},
    "Sri Lanka":           {"iso3": "LKA", "centroid": (80.7718,   7.8731), "zoom": 7},
    "Tajikistan":          {"iso3": "TJK", "centroid": (71.2761,  38.8610), "zoom": 7},
    "Thailand":            {"iso3": "THA", "centroid": (100.9925,  15.8700),"zoom": 6},
    "Timor-Leste":         {"iso3": "TLS", "centroid": (125.7275,  -8.8742),"zoom": 8},
    "Turkmenistan":        {"iso3": "TKM", "centroid": (58.7793,  38.9697), "zoom": 6},
    "Uzbekistan":          {"iso3": "UZB", "centroid": (64.5853,  41.3775), "zoom": 6},
    "Vanuatu":             {"iso3": "VUT", "centroid": (166.9592, -15.3767),"zoom": 7},
    "Vietnam":             {"iso3": "VNM", "centroid": (108.2772,  14.0583),"zoom": 6},

    # ── LATIN AMERICA & CARIBBEAN ───────────────────────────────────────── #
    "Argentina":           {"iso3": "ARG", "centroid": (-63.6167, -38.4161),"zoom": 4},
    "Bolivia":             {"iso3": "BOL", "centroid": (-64.9631, -16.2902),"zoom": 6},
    "Brazil":              {"iso3": "BRA", "centroid": (-51.9253, -14.2350),"zoom": 4},
    "Chile":               {"iso3": "CHL", "centroid": (-71.5430, -35.6751),"zoom": 5},
    "Colombia":            {"iso3": "COL", "centroid": (-74.2973,   4.5709),"zoom": 6},
    "Costa Rica":          {"iso3": "CRI", "centroid": (-83.7534,   9.7489),"zoom": 7},
    "Cuba":                {"iso3": "CUB", "centroid": (-79.5197,  21.5218),"zoom": 7},
    "Dominican Republic":  {"iso3": "DOM", "centroid": (-70.1627,  18.7357),"zoom": 8},
    "Ecuador":             {"iso3": "ECU", "centroid": (-78.1834,  -1.8312),"zoom": 7},
    "El Salvador":         {"iso3": "SLV", "centroid": (-88.8965,  13.7942),"zoom": 8},
    "Guatemala":           {"iso3": "GTM", "centroid": (-90.2308,  15.7835),"zoom": 7},
    "Haiti":               {"iso3": "HTI", "centroid": (-72.2852,  18.9712),"zoom": 8},
    "Honduras":            {"iso3": "HND", "centroid": (-86.2419,  15.1999),"zoom": 7},
    "Jamaica":             {"iso3": "JAM", "centroid": (-77.2975,  18.1096),"zoom": 9},
    "Mexico":              {"iso3": "MEX", "centroid": (-102.5528,  23.6345),"zoom": 5},
    "Nicaragua":           {"iso3": "NIC", "centroid": (-85.2072,  12.8654),"zoom": 7},
    "Panama":              {"iso3": "PAN", "centroid": (-80.7821,   8.5380),"zoom": 7},
    "Paraguay":            {"iso3": "PRY", "centroid": (-58.4438, -23.4425),"zoom": 6},
    "Peru":                {"iso3": "PER", "centroid": (-75.0152,  -9.1900),"zoom": 6},
    "Trinidad and Tobago": {"iso3": "TTO", "centroid": (-61.2225,  10.6918),"zoom": 9},
    "Uruguay":             {"iso3": "URY", "centroid": (-55.7658, -32.5228),"zoom": 7},
    "Venezuela":           {"iso3": "VEN", "centroid": (-66.5897,   6.4238),"zoom": 6},

    # ── EUROPE & CENTRAL ASIA ───────────────────────────────────────────── #
    "Albania":             {"iso3": "ALB", "centroid": (20.1683,  41.1533), "zoom": 8},
    "Armenia":             {"iso3": "ARM", "centroid": (45.0382,  40.0691), "zoom": 8},
    "Azerbaijan":          {"iso3": "AZE", "centroid": (47.5769,  40.1431), "zoom": 7},
    "Belarus":             {"iso3": "BLR", "centroid": (27.9534,  53.7098), "zoom": 6},
    "Bosnia & Herzegovina":{"iso3": "BIH", "centroid": (17.6791,  43.9159), "zoom": 8},
    "Bulgaria":            {"iso3": "BGR", "centroid": (25.4858,  42.7339), "zoom": 7},
    "France":              {"iso3": "FRA", "centroid": (2.2137,   46.2276), "zoom": 6},
    "Georgia":             {"iso3": "GEO", "centroid": (43.3569,  42.3154), "zoom": 7},
    "Germany":             {"iso3": "DEU", "centroid": (10.4515,  51.1657), "zoom": 6},
    "Greece":              {"iso3": "GRC", "centroid": (21.8243,  39.0742), "zoom": 7},
    "Hungary":             {"iso3": "HUN", "centroid": (19.5033,  47.1625), "zoom": 7},
    "Italy":               {"iso3": "ITA", "centroid": (12.5674,  41.8719), "zoom": 6},
    "Moldova":             {"iso3": "MDA", "centroid": (28.3699,  47.4116), "zoom": 7},
    "Netherlands":         {"iso3": "NLD", "centroid": (5.2913,   52.1326), "zoom": 7},
    "North Macedonia":     {"iso3": "MKD", "centroid": (21.7453,  41.6086), "zoom": 8},
    "Poland":              {"iso3": "POL", "centroid": (19.1451,  51.9194), "zoom": 6},
    "Portugal":            {"iso3": "PRT", "centroid": (-8.2245,  39.3999), "zoom": 7},
    "Romania":             {"iso3": "ROU", "centroid": (24.9668,  45.9432), "zoom": 6},
    "Russia":              {"iso3": "RUS", "centroid": (105.3188,  61.5240),"zoom": 3},
    "Serbia":              {"iso3": "SRB", "centroid": (21.0059,  44.0165), "zoom": 7},
    "Spain":               {"iso3": "ESP", "centroid": (-3.7492,  40.4637), "zoom": 6},
    "Ukraine":             {"iso3": "UKR", "centroid": (31.1656,  48.3794), "zoom": 6},
    "United Kingdom":      {"iso3": "GBR", "centroid": (-3.4360,  55.3781), "zoom": 6},
    "Uzbekistan":          {"iso3": "UZB", "centroid": (64.5853,  41.3775), "zoom": 6},

    # ── NORTH AMERICA ───────────────────────────────────────────────────── #
    "Canada":              {"iso3": "CAN", "centroid": (-96.8165,  56.1304),"zoom": 4},
    "United States":       {"iso3": "USA", "centroid": (-95.7129,  37.0902),"zoom": 4},
}

DEFAULT_COUNTRY = "Kenya"

# --------------------------------------------------------------------------- #
# SoilGrids 2.0 — ISRIC
# Docs: https://www.isric.org/explore/soilgrids
# --------------------------------------------------------------------------- #
SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# Properties we surface in the dashboard. Each has:
#   - layer: SoilGrids property code
#   - unit: display unit
#   - conversion: factor to apply to raw SoilGrids value to get display unit
#     (SoilGrids stores most values multiplied by 10 or 100 for integer packing)
#   - depth: primary depth interval used
SOIL_PROPERTIES = {
    "soc": {
        "layer": "soc",
        "label": "Soil Organic Carbon",
        "unit": "g/kg",
        "conversion": 0.1,   # dg/kg -> g/kg
        "depth": "0-5cm",
        "good_above": 15.0,  # g/kg — FAO healthy threshold
    },
    "phh2o": {
        "layer": "phh2o",
        "label": "pH (H₂O)",
        "unit": "",
        "conversion": 0.1,   # pH*10 -> pH
        "depth": "0-5cm",
        "optimal_range": (6.0, 7.5),
    },
    "clay": {
        "layer": "clay",
        "label": "Clay",
        "unit": "%",
        "conversion": 0.1,
        "depth": "0-5cm",
    },
    "sand": {
        "layer": "sand",
        "label": "Sand",
        "unit": "%",
        "conversion": 0.1,
        "depth": "0-5cm",
    },
    "nitrogen": {
        "layer": "nitrogen",
        "label": "Total Nitrogen",
        "unit": "g/kg",
        "conversion": 0.01,  # cg/kg -> g/kg
        "depth": "0-5cm",
        "good_above": 1.5,
    },
    "cec": {
        "layer": "cec",
        "label": "Cation Exchange Capacity",
        "unit": "cmol(+)/kg",
        "conversion": 0.1,
        "depth": "0-5cm",
        "good_above": 15.0,
    },
    "bdod": {
        "layer": "bdod",
        "label": "Bulk Density",
        "unit": "g/cm³",
        "conversion": 0.01,
        "depth": "0-5cm",
        "good_below": 1.4,  # compaction threshold
    },
}

# --------------------------------------------------------------------------- #
# RUSLE erosion model — risk classes (t/ha/yr)
# Based on FAO (2019) and OECD erosion risk tiers
# --------------------------------------------------------------------------- #
EROSION_CLASSES = [
    (0, 2,    "Very Low",  "#2d6a4f"),
    (2, 5,    "Low",       "#52b788"),
    (5, 10,   "Moderate",  "#f4a261"),
    (10, 25,  "High",      "#e76f51"),
    (25, 1e9, "Very High", "#9d0208"),
]

# --------------------------------------------------------------------------- #
# Soil health scorecard weights — sum must equal 1.0
# Weights reflect agronomic importance for smallholder rainfed systems.
# --------------------------------------------------------------------------- #
SCORECARD_WEIGHTS = {
    "soc":      0.30,
    "phh2o":    0.15,
    "nitrogen": 0.20,
    "cec":      0.15,
    "bdod":     0.10,
    "texture":  0.10,  # derived from sand/clay balance
}

# --------------------------------------------------------------------------- #
# NDVI / GEE settings
# --------------------------------------------------------------------------- #
GEE_COLLECTIONS = {
    "ndvi_modis":   "MODIS/061/MOD13Q1",       # 250 m, 16-day
    "precip_chirps":"UCSB-CHG/CHIRPS/DAILY",   # 5 km daily rainfall
    "dem_srtm":     "USGS/SRTMGL1_003",         # 30 m elevation
    "landcover":    "ESA/WorldCover/v200",      # 10 m land cover (2021)
}

NDVI_SCALE = 0.0001  # MOD13Q1 scaling factor
