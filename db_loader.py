import pandas as pd
import duckdb
import os
import requests

# API_ENDPOINT = "https://api.example.com/observability/breaches"
# API_KEY = "api_key"

# def fetch_api_data():
#     
#    ## Fetching real-time observability metrics from an external API like Grafana, Datadog
#     
#     print(f"Fetching live data from {API_ENDPOINT}...")
#     
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json"
#     }
#     
#     try:
#         # response = requests.get(API_ENDPOINT, headers=headers)
#         # response.raise_for_status()
#         # raw_json = response.json()
#         
#         # --- MOCK PAYLOAD FOR NOW ---
#         print("Using mock API payload since endpoint is a placeholder...")
#         raw_json = {
#             "data": [
#                 {"week": "Week 5", "service": "OneBank.APIGateWay", "breaches": 450, "type": "Latency"},
#                 {"week": "Week 5", "service": "xplorer-case-api", "breaches": 120, "type": "Error rate"},
#                 {"week": "Week 5", "service": "Core-Banking-USSD", "breaches": 85, "type": "Health Check"}
#             ]
#         }
#         # -----------------------------
# 
#         # Convert JSON directly into a pandas DataFrame
#         df_api = pd.DataFrame(raw_json["data"])
#         
#         # Standardize column names to match our DuckDB schema
#         df_api.rename(columns={
#             "service": "microservice",
#             "breaches": "breach_count",
#             "type": "breach_type"
#         }, inplace=True)
#         
#         return df_api
#         
#     except Exception as e:
#         print(f"API Fetch failed: {e}")
#         return pd.DataFrame()


_script_dir = os.path.dirname(os.path.abspath(__file__))
excel_file = os.path.join(os.path.expanduser("~/Downloads"), "Service Breach Data.xlsx")
db_file = os.path.join(_script_dir, "breaches.duckdb")

def clean_and_load():
    print("Connecting to DuckDB database...")
    # DuckDB creates the file if needed
    conn = duckdb.connect(db_file)
    
    # Weekly sheets
    weekly_sheet_mapping = {
        'Week 1': 'Week 1',
        'Week 2': 'Week 2',
        'W': 'Week 3',
        '24th - 30th': 'Week 4'
    }
    

    conn.execute("DROP TABLE IF EXISTS weekly_breaches_raw")
    conn.execute("""
    CREATE TABLE weekly_breaches_raw (
        week VARCHAR,
        microservice VARCHAR,
        breach_count INTEGER,
        breach_type VARCHAR
    )
    """)
    
    raw_rows_inserted = 0
    for src_sheet, std_week in weekly_sheet_mapping.items():
        print(f"Reading raw sheet '{src_sheet}' as '{std_week}'...")
        df = pd.read_excel(excel_file, sheet_name=src_sheet)
        
        # Clean service names
        df['Microservice'] = df['Microservice'].astype(str).str.strip()
        
        # Standardise casing
        df.loc[df['Microservice'].str.lower() == 'eacbs', 'Microservice'] = 'EACBS'
        

        df['Breach Type'] = df['Breach Type'].fillna('Unknown').astype(str).str.strip()
        

        df['week'] = std_week
        

        df_clean = df[['week', 'Microservice', 'Breach Count', 'Breach Type']].copy()
        df_clean.columns = ['week', 'microservice', 'breach_count', 'breach_type']
        

        conn.execute("INSERT INTO weekly_breaches_raw SELECT * FROM df_clean")
        raw_rows_inserted += len(df_clean)
            
    print(f"Loaded {raw_rows_inserted} rows into 'weekly_breaches_raw' table")
    
    # Tier 1 & 2 sheet
    print("Reading Tier 1 & 2 sheet '1st - 2nd'...")
    df_t12 = pd.read_excel(excel_file, sheet_name='1st - 2nd')
    
    df_t12['Microservice'] = df_t12['Microservice'].astype(str).str.strip()
    df_t12.loc[df_t12['Microservice'].str.lower() == 'eacbs', 'Microservice'] = 'EACBS'
    df_t12['Breach Type'] = df_t12['Breach Type'].fillna('Unknown').astype(str).str.strip()
    df_t12['Week'] = df_t12['Week'].astype(str).str.strip()
    
    df_t12_clean = df_t12[['Week', 'Microservice', 'Breach Count', 'Breach Type']].copy()
    df_t12_clean.columns = ['week', 'microservice', 'breach_count', 'breach_type']
    
    conn.execute("DROP TABLE IF EXISTS tier_1_2_breaches")
    conn.execute("""
    CREATE TABLE tier_1_2_breaches (
        week VARCHAR,
        microservice VARCHAR,
        breach_count INTEGER,
        breach_type VARCHAR
    )
    """)
    conn.execute("INSERT INTO tier_1_2_breaches SELECT * FROM df_t12_clean")
    t12_rows_inserted = len(df_t12_clean)
        
    print(f"Loaded {t12_rows_inserted} rows into 'tier_1_2_breaches' table")
    
    # Fetch and load API data (Commented out until i have a real API)
    # df_api = fetch_api_data()
    # if not df_api.empty:
    #     conn.execute("INSERT INTO weekly_breaches_raw SELECT * FROM df_api")
    #     print(f"Loaded {len(df_api)} rows from API into 'weekly_breaches_raw' table")


    
    conn.close()
    print("DuckDB data loading completed successfully!")

if __name__ == "__main__":
    clean_and_load()
