import os
import logging

# logging setup
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO

def setup_logging(name: str) -> logging.Logger:
    """Get standard logger."""
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    return logger

# paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# File Paths
DB_FILE = os.path.join(SCRIPT_DIR, "breaches.duckdb")
OUTPUT_IMAGE_SYSTEM = os.path.join(SCRIPT_DIR, "breach_dashboard_system.png")
OUTPUT_IMAGE_TIER = os.path.join(SCRIPT_DIR, "breach_dashboard_tier.png")
OUTPUT_IMAGE = OUTPUT_IMAGE_SYSTEM  # Legacy alias
EMAIL_CONFIG_FILE = os.path.join(SCRIPT_DIR, "email_config.json")
SIMULATED_HTML_OUTPUT = os.path.join(SCRIPT_DIR, "simulated_email.html")

# Excel Sheet Names Configuration
WEEKLY_SHEET_MAPPING = {
    'Week 1': 'Week 1',
    'Week 2': 'Week 2',
    'W': 'Week 3',
    '24th - 30th': 'Week 4'
}
TIER_1_2_SHEET = '1st - 2nd'

# check local dir first, fallback to user Downloads
EXCEL_FILE_LOCAL = os.path.join(SCRIPT_DIR, "Service Breach Data.xlsx")
EXCEL_FILE_DOWNLOADS = os.path.join(os.path.expanduser("~/Downloads"), "Service Breach Data.xlsx")

if os.path.exists(EXCEL_FILE_LOCAL):
    EXCEL_FILE = EXCEL_FILE_LOCAL
else:
    EXCEL_FILE = EXCEL_FILE_DOWNLOADS

# API Configuration
ENABLE_API_FETCH = os.environ.get("ENABLE_API_FETCH", "False").lower() in ("true", "1", "yes")
API_ENDPOINT = os.environ.get("OBSERVABILITY_API_ENDPOINT", "https://api.example.com/observability/breaches")
API_KEY = os.environ.get("OBSERVABILITY_API_KEY", "placeholder_api_key")

# SLA thresholds
SLA_THRESHOLDS = {
    "total_breaches": 10000,
    "error_breach_ratio": 30.0,       # Max acceptable % of errors
    "latency_breach_ratio": 70.0,     # Max acceptable % of latency
    "tier_1_2_contribution": 5.0      # Max acceptable % of breaches in critical channels
}

# schema validation
REQUIRED_RAW_COLUMNS = ["Microservice", "Breach Count", "Breach Type"]
REQUIRED_T12_COLUMNS = ["Week", "Microservice", "Breach Count", "Breach Type"]

# Standardizations
CASING_STANDARDIZATION = {
    "eacbs": "EACBS",
    "onebank.apigateway": "OneBank.APIGateWay",
    "xplorer-case-api": "xplorer-case-api",
    "core-banking-ussd": "Core-Banking-USSD",
    "core-banking-sms": "Core-Banking-SMS",
    "core-banking-otp": "Core-Banking-OTP"
}

BREACH_TYPE_MAPPING = {
    "Error rate": [
        "error rate", "availability", "health check", "failed count", 
        "failure rate & failed count"
    ],
    "Latency": [
        "latency", "consumer lag", "pending count", "pending rate & pending count",
        "frozen jobs", "unsynced count", "high disk usage on d:"
    ]
}

def standardize_breach_type(raw_type: str) -> str:
    """Classifies raw breach types into core categories (Error rate, Latency, Unknown)."""
    if not isinstance(raw_type, str):
        return "Unknown"
    
    cleaned = raw_type.strip().lower()
    for core_type, raw_variants in BREACH_TYPE_MAPPING.items():
        if cleaned in raw_variants:
            return core_type
    return "Unknown"

def standardize_microservice(raw_name: str) -> str:
    """Cleans whitespace and standardizes common microservice names to correct casing."""
    if not isinstance(raw_name, str):
        return "Unknown"
    
    cleaned = raw_name.strip()
    lower_cleaned = cleaned.lower()
    
    # Return the mapped standard casing if found, otherwise return the cleaned string
    return CASING_STANDARDIZATION.get(lower_cleaned, cleaned)
