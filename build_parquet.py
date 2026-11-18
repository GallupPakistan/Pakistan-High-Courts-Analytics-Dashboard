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
import hashlib
import boto3

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env in the same folder if present (local runs)
except ImportError:
    pass

OUT_PATH = "data/combined_dashboard_master.parquet"

# DynamoDB destination. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are picked up
# from the environment by boto3 — never hardcode credentials here.
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
DDB_TABLE = os.environ.get("DYNAMODB_TABLE", "PakistanCourtCases")

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
    "PHC_Benches": {
        "repo": "GallupPakistan/PHC-Dasboard",
        "path": "scripts/phc_benches_combined.parquet",
        "kind": "parquet",
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
        return pd.Series([""] * len(df), index=df.index)

    title = col("Title").astype(str)
    split = title.str.split(r"\s+[Vv][Ss]\.?\s+", n=1, expand=True)
    petitioner = split[0] if 0 in split.columns else title
    respondent = split[1] if 1 in split.columns else pd.Series([""] * len(df), index=df.index)

    out = pd.DataFrame({
        "Court": "Lahore High Court",
        "Date": col("Hearing Date"),
        "Case_No": col("Case#"),
        "Section": col("Category"),
        "Judges": col("Justice"),
        "Petitioner": petitioner,
        "Respondent": respondent,
        "Petitioner_Advocate": col("Lawyer"),
        "Respondent_Advocate": "",
        "Source_File": col("Source_File"),
    }, index=df.index)
    print(f"LHC columns found in file: {list(df.columns)}")
    return out


def load_phc_benches():
    data = fetch_bytes(SOURCES["PHC_Benches"]["repo"], SOURCES["PHC_Benches"]["path"])
    df = pd.read_parquet(io.BytesIO(data))
    bench_labels = df.get("Bench", "").astype(str)
    out = pd.DataFrame({
        "Court": "Peshawar High Court - " + bench_labels,
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
        "PHC_Benches": load_phc_benches,
        "Sindh": load_sindh,
        "LHC": load_lhc,
        "IHC": load_ihc,
    }
    frames = []
    all_ok = True
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
            all_ok = False

    if not frames:
        print("No data loaded from any source. Aborting.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.astype(str)

    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        print("AWS credentials not set — skipping DynamoDB upload.")
        return

    # Exact duplicate rows are dropped by the dashboard anyway.
    combined = combined.drop_duplicates().reset_index(drop=True)

    # Stable row ID = hash of all columns, so re-runs only add genuinely new rows.
    key = combined[UNIFIED_COLS[0]]
    for c in UNIFIED_COLS[1:]:
        key = key + "\x1f" + combined[c]
    combined["row_id"] = key.map(lambda x: hashlib.sha1(x.encode("utf-8")).hexdigest())

    table = boto3.resource("dynamodb", region_name=AWS_REGION).Table(DDB_TABLE)

    # IDs already in the table
    have, kwargs = set(), {"ProjectionExpression": "row_id"}
    while True:
        r = table.scan(**kwargs)
        have.update(i["row_id"] for i in r["Items"])
        if "LastEvaluatedKey" not in r:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    print(f"Table already has {len(have)} rows")

    # Write only new rows
    new = combined[~combined["row_id"].isin(have)]
    with table.batch_writer() as bw:
        for n, rec in enumerate(new.to_dict("records"), 1):
            bw.put_item(Item=rec)
            if n % 50000 == 0:
                print(f"  written {n}/{len(new)}")
    print(f"{len(new)} new rows written")

    # Remove stale rows, but only if every source loaded
    # (otherwise a failed source's data would be deleted by mistake).
    if all_ok:
        stale = have - set(combined["row_id"])
        with table.batch_writer() as bw:
            for rid in stale:
                bw.delete_item(Key={"row_id": rid})
        print(f"{len(stale)} stale rows removed")
    else:
        print("A source failed this run — skipping stale-row cleanup.")

    print(f"\nDone. {len(combined)} rows in source -> DynamoDB {AWS_REGION}/{DDB_TABLE}")


if __name__ == "__main__":
    main()
