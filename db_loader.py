import os
import sys
import pandas as pd
import duckdb
import requests
import config

logger = config.setup_logging("db_loader")

def fetch_api_data() -> pd.DataFrame:
    """Fetch observability data from live API if enabled."""
    if not config.ENABLE_API_FETCH:
        logger.info("External API fetch is disabled.")
        return pd.DataFrame()
        
    logger.info(f"Fetching from: {config.API_ENDPOINT}...")
    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(config.API_ENDPOINT, headers=headers, timeout=10)
        response.raise_for_status()
        raw_json = response.json()
        
        data_list = raw_json.get("data", [])
        if not data_list:
            logger.warning("Empty API data array.")
            return pd.DataFrame()
            
        df_api = pd.DataFrame(data_list)
        logger.info(f"Fetched {len(df_api)} rows.")
        return df_api
        
    except Exception as e:
        logger.error(f"API Fetch failed: {e}. Using empty dataframe fallback.")
        return pd.DataFrame()


def validate_and_clean_columns(df: pd.DataFrame, expected_cols: list, sheet_name: str) -> pd.DataFrame:
    """Ensure expected columns exist and standardize their casing."""
    df_cols_lower = [c.lower() for c in df.columns]
    missing_cols = []
    
    col_mapping = {}
    for req in expected_cols:
        if req.lower() not in df_cols_lower:
            missing_cols.append(req)
        else:
            actual_name = df.columns[df_cols_lower.index(req.lower())]
            col_mapping[actual_name] = req
            
    if missing_cols:
        raise ValueError(f"Sheet '{sheet_name}' is missing columns: {missing_cols}")
        
    return df[list(col_mapping.keys())].rename(columns=col_mapping)


def profile_missing_values(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Check for missing values and fill them."""
    df_cleaned = df.copy()
    
    for col in df_cleaned.columns:
        null_count = df_cleaned[col].isnull().sum()
        if null_count > 0:
            logger.warning(f"Sheet '{sheet_name}' has {null_count} nulls in '{col}'.")
            
            if col == "Breach Count":
                df_cleaned[col] = df_cleaned[col].fillna(0)
            else:
                df_cleaned[col] = df_cleaned[col].fillna("Unknown")
                
    return df_cleaned


def validate_data_types(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Enforce data types on columns."""
    df_cleaned = df.copy()
    
    for str_col in ["Microservice", "Breach Type"]:
        if str_col in df_cleaned.columns:
            df_cleaned[str_col] = df_cleaned[str_col].astype(str).str.strip()
            
    if "Week" in df_cleaned.columns:
        df_cleaned["Week"] = df_cleaned["Week"].astype(str).str.strip()
        
    if "Breach Count" in df_cleaned.columns:
        original_nulls = df_cleaned["Breach Count"].isnull().sum()
        df_cleaned["Breach Count"] = pd.to_numeric(df_cleaned["Breach Count"], errors='coerce')
        new_nulls = df_cleaned["Breach Count"].isnull().sum()
        
        coerced_count = new_nulls - original_nulls
        if coerced_count > 0:
            logger.warning(f"Coerced {coerced_count} invalid Breach Counts to NaN in sheet '{sheet_name}'.")
            df_cleaned["Breach Count"] = df_cleaned["Breach Count"].fillna(0)
            
        df_cleaned["Breach Count"] = df_cleaned["Breach Count"].astype(int)
        
    return df_cleaned


def detect_and_remove_duplicates(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Remove row duplicates."""
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        logger.warning(f"Found {dup_count} duplicate rows in sheet '{sheet_name}'. Dropping duplicates.")
        return df.drop_duplicates()
    return df


def clean_and_load() -> None:
    """Extract, clean, and load Excel data into DuckDB."""
    logger.info("Starting ETL process...")
    
    if not os.path.exists(config.EXCEL_FILE):
        logger.critical(f"Excel file not found at: {config.EXCEL_FILE}")
        raise FileNotFoundError(f"Missing input source file: {config.EXCEL_FILE}")
        
    logger.info(f"Source Excel file located at: {config.EXCEL_FILE}")
    
    conn = None
    try:
        # scan excel sheets
        excel_reader = pd.ExcelFile(config.EXCEL_FILE)
        all_sheets = excel_reader.sheet_names
        logger.info(f"Detected sheets in Excel file: {all_sheets}")
        
        active_week_mapping = config.WEEKLY_SHEET_MAPPING.copy()
        
        # map sheets matching 'Week X' dynamically
        for sheet in all_sheets:
            if sheet not in active_week_mapping and sheet != config.TIER_1_2_SHEET:
                sheet_lower = sheet.strip().lower()
                if sheet_lower.startswith("week") or sheet_lower.startswith("w"):
                    digits = ''.join(filter(str.isdigit, sheet))
                    if digits:
                        std_name = f"Week {digits}"
                        active_week_mapping[sheet] = std_name
                        logger.info(f"Dynamically mapped sheet '{sheet}' to standardized name '{std_name}'.")
        
        logger.info(f"Weekly sheets to process: {list(active_week_mapping.keys())}")
        
        # db setup
        logger.info(f"Connecting to DuckDB database at {config.DB_FILE}...")
        conn = duckdb.connect(config.DB_FILE)
        
        conn.execute("DROP TABLE IF EXISTS weekly_breaches_raw")
        conn.execute("""
            CREATE TABLE weekly_breaches_raw (
                week VARCHAR,
                microservice VARCHAR,
                breach_count INTEGER,
                breach_type VARCHAR,
                core_breach_type VARCHAR
            )
        """)
        
        # ingest weekly sheets
        raw_rows_inserted = 0
        weekly_dfs = {}
        
        for src_sheet, std_week in active_week_mapping.items():
            if src_sheet not in all_sheets:
                logger.warning(f"Configured sheet '{src_sheet}' not found in Excel file. Skipping.")
                continue
                
            logger.info(f"Reading sheet '{src_sheet}' (standardized as '{std_week}')...")
            df = pd.read_excel(config.EXCEL_FILE, sheet_name=src_sheet)
            
            df = validate_and_clean_columns(df, config.REQUIRED_RAW_COLUMNS, src_sheet)
            df = profile_missing_values(df, src_sheet)
            df = validate_data_types(df, src_sheet)
            df = detect_and_remove_duplicates(df, src_sheet)
            
            df['microservice'] = df['Microservice'].apply(config.standardize_microservice)
            df['breach_count'] = df['Breach Count']
            df['breach_type'] = df['Breach Type']
            df['core_breach_type'] = df['Breach Type'].apply(config.standardize_breach_type)
            df['week'] = std_week
            
            df_to_insert = df[['week', 'microservice', 'breach_count', 'breach_type', 'core_breach_type']].copy()
            weekly_dfs[std_week] = df_to_insert
            
            conn.execute("INSERT INTO weekly_breaches_raw SELECT * FROM df_to_insert")
            raw_rows_inserted += len(df_to_insert)
            logger.info(f"Successfully loaded {len(df_to_insert)} rows for '{std_week}' into database.")
            
        logger.info(f"Total weekly raw rows loaded: {raw_rows_inserted}")
        
        # ingest tier 1 & 2 channel sheet
        if config.TIER_1_2_SHEET not in all_sheets:
            logger.error(f"Critical sheet '{config.TIER_1_2_SHEET}' is missing from the Excel file!")
            raise ValueError(f"Missing required sheet: {config.TIER_1_2_SHEET}")
            
        logger.info(f"Reading Tier 1 & 2 sheet '{config.TIER_1_2_SHEET}'...")
        df_t12 = pd.read_excel(config.EXCEL_FILE, sheet_name=config.TIER_1_2_SHEET)
        
        df_t12 = validate_and_clean_columns(df_t12, config.REQUIRED_T12_COLUMNS, config.TIER_1_2_SHEET)
        df_t12 = profile_missing_values(df_t12, config.TIER_1_2_SHEET)
        df_t12 = validate_data_types(df_t12, config.TIER_1_2_SHEET)
        df_t12 = detect_and_remove_duplicates(df_t12, config.TIER_1_2_SHEET)
        
        df_t12['week'] = df_t12['Week']
        df_t12['microservice'] = df_t12['Microservice'].apply(config.standardize_microservice)
        df_t12['breach_count'] = df_t12['Breach Count']
        df_t12['breach_type'] = df_t12['Breach Type']
        df_t12['core_breach_type'] = df_t12['Breach Type'].apply(config.standardize_breach_type)
        
        df_t12_to_insert = df_t12[['week', 'microservice', 'breach_count', 'breach_type', 'core_breach_type']].copy()
        
        # check for duplicate weeks
        t12_weeks = df_t12_to_insert['week'].unique()
        for i in range(len(t12_weeks)):
            for j in range(i + 1, len(t12_weeks)):
                w1 = t12_weeks[i]
                w2 = t12_weeks[j]
                
                df_w1 = df_t12_to_insert[df_t12_to_insert['week'] == w1][['microservice', 'breach_count', 'breach_type']].sort_values(by='microservice').reset_index(drop=True)
                df_w2 = df_t12_to_insert[df_t12_to_insert['week'] == w2][['microservice', 'breach_count', 'breach_type']].sort_values(by='microservice').reset_index(drop=True)
                
                if not df_w1.empty and not df_w2.empty and df_w1.equals(df_w2):
                    logger.critical(
                        f"DATA INTEGRITY ALERT: The breach records in the Tier 1 & 2 sheet for '{w1}' and '{w2}' "
                        f"are 100% IDENTICAL across all services. This indicates a copy-paste duplication error in the source file!"
                    )
        
        conn.execute("DROP TABLE IF EXISTS tier_1_2_breaches")
        conn.execute("""
            CREATE TABLE tier_1_2_breaches (
                week VARCHAR,
                microservice VARCHAR,
                breach_count INTEGER,
                breach_type VARCHAR,
                core_breach_type VARCHAR
            )
        """)
        conn.execute("INSERT INTO tier_1_2_breaches SELECT * FROM df_t12_to_insert")
        logger.info(f"Successfully loaded {len(df_t12_to_insert)} rows into 'tier_1_2_breaches' table.")
        
        # process live API data
        df_api = fetch_api_data()
        if not df_api.empty:
            api_rename_map = {
                "service": "Microservice",
                "breaches": "Breach Count",
                "type": "Breach Type",
                "week": "Week"
            }
            df_api = df_api.rename(columns={k: v for k, v in api_rename_map.items() if k in df_api.columns})
            
            expected_api_cols = ["Week", "Microservice", "Breach Count", "Breach Type"]
            df_api = validate_and_clean_columns(df_api, expected_api_cols, "Live API Endpoint")
            df_api = profile_missing_values(df_api, "Live API Endpoint")
            df_api = validate_data_types(df_api, "Live API Endpoint")
            df_api = detect_and_remove_duplicates(df_api, "Live API Endpoint")
            
            df_api['week'] = df_api['Week']
            df_api['microservice'] = df_api['Microservice'].apply(config.standardize_microservice)
            df_api['breach_count'] = df_api['Breach Count']
            df_api['breach_type'] = df_api['Breach Type']
            df_api['core_breach_type'] = df_api['Breach Type'].apply(config.standardize_breach_type)
            
            df_api_to_insert = df_api[['week', 'microservice', 'breach_count', 'breach_type', 'core_breach_type']].copy()
            conn.execute("INSERT INTO weekly_breaches_raw SELECT * FROM df_api_to_insert")
            logger.info(f"Successfully loaded {len(df_api_to_insert)} live API rows into 'weekly_breaches_raw'.")
            
        logger.info("DuckDB data loading completed successfully!")
        
    except Exception as e:
        logger.exception("An error occurred during the ETL process.")
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            logger.info("DuckDB connection closed.")

if __name__ == "__main__":
    clean_and_load()
