#!/usr/bin/env python3
"""
Google Forms Data Ingest Script for Trusted Data Now

This script fetches data directly from Google Sheets and synchronizes it with
the data.json file, handling additions, updates, and removals with deduplication
and data normalization.

ESIP Federation Disasters Cluster Project
Contributor: Jeil Oh (jeoh@utexas.edu)
"""

import csv, json, sys, re, os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from io import StringIO

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

DEBUG = os.environ.get("INGEST_DEBUG") == "1"

# ---------- helpers ----------
def norm(s): return (s or "").strip()

def to_bool(val, default=False):
    if val is None: return default
    s = str(val).strip().lower()
    if s in ("true","yes","y","1","on","checked"): return True
    if s in ("false","no","n","0","off","unchecked",""): return False
    return default

def normalize_url(u: str) -> str:
    """Lowercase scheme/host, drop utm_* params, trim trailing slash."""
    u = norm(u)
    if not u: return u
    parts = urlsplit(u)
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    path = parts.path[:-1] if parts.path.endswith("/") and parts.path != "/" else parts.path
    q = [(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunsplit((scheme, netloc, path, urlencode(q), ""))

def detect_column(headers, *candidates):
    for i, h in enumerate(headers):
        key = re.sub(r'[^a-z0-9]+',' ', h.lower()).strip()
        for cand in candidates:
            if key == cand or key.startswith(cand) or cand in key.split():
                return i
    return None

def split_multi(s: str):
    """Split checkbox aggregate values from Google Forms CSV."""
    if not s: return []
    # Split on comma, semicolon, or newline; keep non-empty trimmed tokens
    parts = re.split(r'[,\n;]+', s)
    return [p.strip() for p in parts if p and p.strip()]

def normalize_type_token(label: str):
    """Map Google Forms labels (Title Case/plurals) to site tokens."""
    t = (label or "").strip().lower()
    t = t.replace("–","-").replace("—","-")
    # Strip "other:" prefix; return token + optional other text
    m = re.match(r'^other:\s*(.+)$', t)
    other_text = None
    if m:
        other_text = m.group(1).strip()
        t = "other"

    alias = {
        # canonical tokens matching Google Form:
        "flood": "flood",
        "earthquake": "earthquake",
        "wildfire": "wildfire",
        "drought": "drought",
        "hurricane": "hurricane",
        "tornado": "tornado",
        "extreme weather": "extreme-weather",
        "other": "other",
        # common plurals/variants
        "wildfires": "wildfire",
        "flooding": "flood",
        "hurricanes": "hurricane",
        "tornados": "tornado",
        "tornadoes": "tornado",
        "earthquakes": "earthquake",
        "droughts": "drought",
    }
    return alias.get(t, t), other_text

# Allowed canonical tokens the site understands (matching Google Form options).
ALLOWED_TYPES = {
    "flood","earthquake","wildfire","drought","hurricane","tornado","extreme-weather","other"
}

# ---------- Google Sheets functions ----------
def fetch_google_sheets_data(sheet_id, credentials_json=None):
    """Fetch data from Google Sheets (public or private) and return as CSV-like rows."""
    
    # Try authenticated access first (for private sheets)
    if GOOGLE_SHEETS_AVAILABLE and credentials_json:
        try:
            if DEBUG:
                print("Attempting authenticated access to Google Sheets...")
            
            # Set up credentials
            creds = Credentials.from_service_account_info(
                json.loads(credentials_json),
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            # Connect to Google Sheets
            gc = gspread.authorize(creds)
            sheet = gc.open_by_key(sheet_id).sheet1
            
            # Get all values
            all_values = sheet.get_all_values()
            
            if DEBUG:
                print(f"Fetched {len(all_values)} rows from Google Sheets via API")
            
            return all_values
            
        except Exception as e:
            if DEBUG:
                print(f"Authenticated access failed: {e}")
            # Fall through to try public access
    
    # Try public access (for public sheets)
    if REQUESTS_AVAILABLE:
        try:
            if DEBUG:
                print("Attempting public access to Google Sheets...")
            
            # Try different URL formats for public Google Sheets
            csv_urls = [
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0",
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0",
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            ]
            
            response = None
            for csv_url in csv_urls:
                if DEBUG:
                    print(f"Trying URL: {csv_url}")
                try:
                    response = requests.get(csv_url)
                    if response.status_code == 200:
                        break
                except:
                    continue
            
            if not response or response.status_code != 200:
                raise Exception(f"Could not access Google Sheet. Status: {response.status_code if response else 'No response'}")
            
            if DEBUG:
                print(f"Successfully fetched from: {csv_url}")
            
            # Parse CSV content
            csv_content = response.text
            csv_reader = csv.reader(StringIO(csv_content))
            rows = list(csv_reader)
            
            if DEBUG:
                print(f"Fetched {len(rows)} rows from public Google Sheets")
            
            return rows
            
        except Exception as e:
            if DEBUG:
                print(f"Public access failed: {e}")
    
    # If both methods failed
    if not GOOGLE_SHEETS_AVAILABLE and not REQUESTS_AVAILABLE:
        print("Error: Neither Google Sheets API nor requests library available.")
        print("Install with: pip install gspread google-auth requests")
        sys.exit(1)
    else:
        print("Error: Could not access Google Sheet with either authenticated or public methods.")
        print("For private sheets, ensure GOOGLE_SHEETS_CREDENTIALS is set correctly.")
        print("For public sheets, ensure the sheet is publicly accessible.")
        sys.exit(1)

def fetch_csv_data(csv_path):
    """Fetch data from local CSV file."""
    with open(csv_path, "r", encoding="utf-8") as f:
        rdr = csv.reader(f)
        return list(rdr)

# ---------- main ----------
def main():
    if len(sys.argv) < 3:
        print("usage: ingest_google_forms.py <data_json_in> <data_json_out> [csv_file_or_sheet_id]")
        print("  - If csv_file_or_sheet_id is a file path: reads from CSV")
        print("  - If csv_file_or_sheet_id is a Google Sheets ID: fetches from Google Sheets")
        print("  - If omitted: uses GOOGLE_SHEETS_ID environment variable")
        sys.exit(2)

    data_in, data_out = sys.argv[1], sys.argv[2]
    
    # Determine data source
    if len(sys.argv) >= 4:
        source = sys.argv[3]
    else:
        source = os.environ.get("GOOGLE_SHEETS_ID")
        if not source:
            print("Error: No data source specified. Provide CSV file, Google Sheets ID, or set GOOGLE_SHEETS_ID environment variable")
            sys.exit(1)
    
    # Fetch data based on source type
    if source.endswith('.csv') or '/' in source or '\\' in source:
        # Treat as CSV file path
        if not os.path.exists(source):
            print(f"Error: CSV file not found: {source}")
            sys.exit(1)
        rows = fetch_csv_data(source)
        if DEBUG:
            print(f"Reading from CSV file: {source}")
    else:
        # Treat as Google Sheets ID
        credentials_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        rows = fetch_google_sheets_data(source, credentials_json)
        if DEBUG:
            print(f"Reading from Google Sheets ID: {source}")

    # Load existing JSON
    with open(data_in, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = []
    if not isinstance(data, list):
        data = []

    # Create lookup maps for existing data
    existing_by_url = {}  # normalized_url -> resource
    existing_urls = set()
    for r in data:
        u = normalize_url(r.get("url",""))
        if u:
            existing_urls.add(u)
            existing_by_url[u] = r

    if not rows:
        print("empty CSV")
        with open(data_out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return

    headers = rows[0]
    idx = {
        "name":          detect_column(headers, "data name","name","resource name"),
        "description":   detect_column(headers, "description"),
        "types":         detect_column(headers, "type","types"),
        "url":           detect_column(headers, "url","link"),
        "organization":  detect_column(headers, "organization","org"),
        "contact":       detect_column(headers, "contact","email"),
        "contributorName": detect_column(headers, "contributor name","contributor"),
        "contributorEmail": detect_column(headers, "contributor email","contributor email"),
        "notes":         detect_column(headers, "notes","note"),
        "subscription":  detect_column(headers, "requires subscription","subscription"),
        "researchOrOps": detect_column(headers, "use case","usecase","research or ops","researchorops"),
        "public":        detect_column(headers, "publicly available","public"),
        "active":        detect_column(headers, "currently active","active"),
    }

    if DEBUG:
        print("Header mapping:", {k: (headers[v] if v is not None else None) for k,v in idx.items()})

    # Process all rows from Google Sheets
    added = 0
    updated = 0
    skipped = []
    new_data = []
    processed_urls = set()

    for n, r in enumerate(rows[1:], start=2):  # CSV row numbers (1=header)
        def cell(ix): return norm(r[ix]) if ix is not None and ix < len(r) else ""

        # Multi-select types
        raw_types = split_multi(cell(idx["types"]))
        normalized_types = []
        other_texts = []
        for raw in raw_types:
            tok, other = normalize_type_token(raw)
            if other: other_texts.append(other)
            if tok in ALLOWED_TYPES:
                normalized_types.append(tok)
            # tolerate legacy tokens that normalize to allowed via alias above

        # Deduplicate and keep order
        seen = set()
        types_final = [t for t in normalized_types if not (t in seen or seen.add(t))]

        # Required fields
        res = {
            "name":         cell(idx["name"]),
            "description":  cell(idx["description"]),
            "url":          cell(idx["url"]),
            "organization": cell(idx["organization"]),
            "contact":      cell(idx["contact"]),
            "contributorName": cell(idx["contributorName"]),
            "contributorEmail": cell(idx["contributorEmail"]),
            "notes":        cell(idx["notes"]),
            "subscription": to_bool(cell(idx["subscription"])),
            "researchOrOps": cell(idx["researchOrOps"]) or "",
            "public":       to_bool(cell(idx["public"]), default=True),
            "active":       to_bool(cell(idx["active"]), default=True),
        }

        reasons = []
        if not res["name"]:        reasons.append("missing name")
        if not res["description"]: reasons.append("missing description")
        if not res["url"]:         reasons.append("missing url")
        if not types_final:        reasons.append("no valid types")

        url_norm = normalize_url(res["url"])
        if not url_norm:           reasons.append("bad url")

        if reasons:
            skipped.append((n, reasons, res, raw_types))
            continue

        # Attach types: array if >1 else single token (keeps diff small; UI supports both)
        res["type"] = types_final if len(types_final) > 1 else types_final[0]

        # If "Other: ..." provided in the form, append to notes
        if other_texts:
            other_note = "Other type(s): " + ", ".join(sorted(set(other_texts)))
            res["notes"] = (res["notes"] + (" | " if res["notes"] else "") + other_note).strip()

        # Set normalized URL
        res["url"] = url_norm
        processed_urls.add(url_norm)

        # Check if this is a new resource or an update
        if url_norm in existing_by_url:
            # Update existing resource
            existing_res = existing_by_url[url_norm]
            # Preserve accessibility data if it exists
            if "accessible" in existing_res:
                res["accessible"] = existing_res["accessible"]
            if "lastChecked" in existing_res:
                res["lastChecked"] = existing_res["lastChecked"]
            if "accessibilityStatus" in existing_res:
                res["accessibilityStatus"] = existing_res["accessibilityStatus"]
            if "accessibilityError" in existing_res:
                res["accessibilityError"] = existing_res["accessibilityError"]
            
            new_data.append(res)
            updated += 1
            if DEBUG:
                print(f"Updated resource: {res['name']}")
        else:
            # New resource
            new_data.append(res)
            added += 1
            if DEBUG:
                print(f"Added new resource: {res['name']}")

    # Find resources that were removed from Google Sheets
    removed = 0
    for url_norm, existing_res in existing_by_url.items():
        if url_norm not in processed_urls:
            removed += 1
            if DEBUG:
                print(f"Removed resource: {existing_res.get('name', 'Unknown')}")

    # Update the data with new/updated resources
    data = new_data

    print(f"Sync complete: Added {added} new, updated {updated} existing, removed {removed} resources.")
    if DEBUG and skipped:
        print(f"Skipped {len(skipped)} row(s):")
        for n, reasons, res, raw_types in skipped[:20]:
            print(f"  - row {n}: {', '.join(reasons)} — types_raw={raw_types} name='{res['name']}' url='{res['url']}'")

    with open(data_out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    main()
