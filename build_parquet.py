"""
Build script for the Pakistan-High-Courts-Analytics-Dashboard (combined repo).

Pulls the latest data from all 5 court-dashboard sources and merges them
into one unified Parquet file (all_courts_combined.parquet) that the
combined dashboard's app.py reads.

Sources:
  - IHC      -> Supabase table
  - BHC      -> raw GitHub xlsx  (GallupPakistan/Balochistan-High-Court)
  - PHC      -> raw GitHub parquet (GallupPakistan/PHC-Dasboard)
  - Sindh    -> raw GitHub xlsx  (GallupPakistan/Sindh_Highcourt_dashboard)
  - LHC      -> raw GitHub xlsx  (GallupPakistan/LHC_DAashboard)

Run:  python build_parquet.py
Env:  SUPABASE_URL, SUPABASE_SERVICE_ROLE  (for IHC)
"""
import os
import io
import requests
import pandas as pd

OUT_PATH = "all_courts_combined.parquet"

RAW = "https://raw.githubusercontent.com/{repo}/main/{path}"

SOURCES = {
    "BHC": {
        "repo": "GallupPakistan/Balochistan-High-Court",
        "path": "data/BHC_Final_File__-_Combined.xlsx",
        "kind": "xlsx",
    },
    "PHC": {
        "repo": "GallupPakistan/PHC-Dasboard",
        "path": "cause_lists_combined_2017_Jan_to_2026_July_MASTER.cache.parquet",
        "kind": "parquet",
    },
    "Sindh": {
        "repo": "GallupPakistan/Sindh_Highcourt_dashboard",
        "path": "sindh_causelist_master/Sindh_Cause_List_Master_Combined.xlsx",
        "kind": "xlsx",
    },
    "LHC": {
        "repo": "GallupPakistan/LHC_DAashboard",
        "path": "combined_data.xlsx",
        "kind": "xlsx",
    },
}

UNIFIED_COLS = [
    "Court", "Date", "Year", "Month", "Day", "Case_No", "Section",
    "Judges", "Petitioner", "Respondent", "Petitioner_Advocate",
    "Respondent_Advocate", "Source_File",
]


def fetch_bytes(repo, path):
    url = RAW.format(repo=repo, path=path)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def load_bhc():
    data = fetch_bytes(SOURCES["BHC"]["repo"], SOURCES["BHC"]["path"])
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
    frames = []
    for sheet_name, df in sheets.items():
        if df.empty:
            continue
        out = pd.DataFrame({
            "Court": "Balochistan High Court",
            "Date": df.get("Date", ""),
            "Case_No": df.get("Case No", ""),
            "Section": df.get("Section", ""),
            "Judges": df.get("Judges", ""),
            "Petitioner": df.get("Petitioner", ""),
            "Respondent": df.get("Respondent", ""),
            "Petitioner_Advocate": df.get("Advocate", ""),
            "Respondent_Advocate": "",
            "Source_File": df.get("Source File", ""),
        })
        frames.append(out)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=UNIFIED_COLS)


def load_phc():
    data = fetch_bytes(SOURCES["PHC"]["repo"], SOURCES["PHC"]["path"])
    df = pd.read_parquet(io.BytesIO(data))
    out = pd.DataFrame({
        "Court": "Peshawar High Court",
        "Date": df.get("Date", ""),
        "Year": df.get("Year", ""),
        "Month": df.get("Month", ""),
        "Day": df.get("Day", ""),
        "Case_No": df.get("Case_No", ""),
        "Section": df.get("Section", ""),
        "Judges": df.get("Judges", ""),
        "Petitioner": df.get("Case_Title", ""),
        "Respondent": "",
        "Petitioner_Advocate": df.get("Petitioner_Advocate", ""),
        "Respondent_Advocate": df.get("Respondent_Advocates", ""),
        "Source_File": df.get("Source_File", ""),
    })
    return out


def load_sindh():
    data = fetch_bytes(SOURCES["Sindh"]["repo"], SOURCES["Sindh"]["path"])
    df = pd.read_excel(io.BytesIO(data))
    out = pd.DataFrame({
        "Court": "Sindh High Court",
        "Date": "",
        "Year": df.get("Year", ""),
        "Month": df.get("Month", ""),
        "Day": df.get("Day", ""),
        "Case_No": df.get("Case_No", ""),
        "Section": df.get("Section", ""),
        "Judges": df.get("Bench", ""),
        "Petitioner": df.get("Petitioner", ""),
        "Respondent": df.get("Respondent", ""),
        "Petitioner_Advocate": df.get("Petitioner_Advocate", ""),
        "Respondent_Advocate": df.get("Respondent_Advocate", ""),
        "Source_File": df.get("City", ""),
    })
    return out


def load_lhc():
    data = fetch_bytes(SOURCES["LHC"]["repo"], SOURCES["LHC"]["path"])
    df = pd.read_excel(io.BytesIO(data))
    cols = {c.lower(): c for c in df.columns}

    def col(*names):
        for n in names:
            if n.lower() in cols:
                return df[cols[n.lower()]]
        return ""

    out = pd.DataFrame({
        "Court": "Lahore High Court",
        "Date": col("Date"),
        "Case_No": col("Case No", "Case_No"),
        "Section": col("Section"),
        "Judges": col("Judges", "Bench"),
        "Petitioner": col("Petitioner"),
        "Respondent": col("Respondent"),
        "Petitioner_Advocate": col("Petitioner Advocate", "Advocate"),
        "Respondent_Advocate": col("Respondent Advocate"),
        "Source_File": "combined_data.xlsx",
    })
    return out


def load_ihc():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE")
    if not url or not key:
        print("SUPABASE_URL/SUPABASE_SERVICE_ROLE not set — skipping IHC.")
        return pd.DataFrame(columns=UNIFIED_COLS)

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    table = "ihc_final"
    limit = 1000
    offset = 0
    rows = []
    while True:
        endpoint = f"{url}/rest/v1/{table}?select=*&limit={limit}&offset={offset}"
        r = requests.get(endpoint, headers=headers, timeout=120)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=UNIFIED_COLS)

    parties = df.get("PARTIES", "")
    out = pd.DataFrame({
        "Court": "Islamabad High Court",
        "Date": df.get("MDATE", ""),
        "Case_No": df.get("CASENO", ""),
        "Section": df.get("CASESTAGENAME", ""),
        "Judges": df.get("BENCHNAME", ""),
        "Petitioner": parties,
        "Respondent": "",
        "Petitioner_Advocate": df.get("ADV1", ""),
        "Respondent_Advocate": df.get("ADV2", ""),
        "Source_File": "supabase:ihc_final",
    })
    return out


def main():
    loaders = {
        "BHC": load_bhc,
        "PHC": load_phc,
        "Sindh": load_sindh,
        "LHC": load_lhc,
        "IHC": load_ihc,
    }
    frames = []
    for name, fn in loaders.items():
        try:
            df = fn()
            for c in UNIFIED_COLS:
                if c not in df.columns:
                    df[c] = ""
            df = df[UNIFIED_COLS]
            frames.append(df)
            print(f"{name}: {len(df)} rows loaded")
        except Exception as e:
            print(f"{name}: FAILED ({e}) — skipping this source for this run")

    if not frames:
        print("No data loaded from any source. Aborting.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.astype(str)
    combined.to_parquet(OUT_PATH, index=False)
    print(f"\nSaved {len(combined)} total rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
