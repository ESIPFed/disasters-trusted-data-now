#!/usr/bin/env python3
"""
Google Forms Data Ingest Script for Trusted Data Now

This script processes CSV exports from Google Forms and adds new resources
to the data.json file, handling deduplication and data normalization.

ESIP Federation Disasters Cluster Project
Contributor: Jeil Oh (jeoh@utexas.edu)
"""

import csv, json, sys, re, os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

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

# ---------- main ----------
def main():
    if len(sys.argv) < 4:
        print("usage: ingest_google_forms.py <csv_in> <data_json_in> <data_json_out>")
        sys.exit(2)

    csv_path, data_in, data_out = sys.argv[1], sys.argv[2], sys.argv[3]

    # Load existing JSON
    with open(data_in, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = []
    if not isinstance(data, list):
        data = []

    # Track duplicates by normalized URL
    existing_urls = set()
    for r in data:
        u = normalize_url(r.get("url",""))
        if u:
            existing_urls.add(u)

    # Read CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        rdr = csv.reader(f)
        rows = list(rdr)

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

    added = 0
    skipped = []

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
        if url_norm in existing_urls:
            reasons.append("duplicate url")

        if reasons:
            skipped.append((n, reasons, res, raw_types))
            continue

        # Attach types: array if >1 else single token (keeps diff small; UI supports both)
        res["type"] = types_final if len(types_final) > 1 else types_final[0]

        # If "Other: ..." provided in the form, append to notes
        if other_texts:
            other_note = "Other type(s): " + ", ".join(sorted(set(other_texts)))
            res["notes"] = (res["notes"] + (" | " if res["notes"] else "") + other_note).strip()

        # Save
        res["url"] = url_norm
        data.append(res)
        existing_urls.add(url_norm)
        added += 1

    print(f"Added {added} new resources.")
    if DEBUG and skipped:
        print(f"Skipped {len(skipped)} row(s):")
        for n, reasons, res, raw_types in skipped[:20]:
            print(f"  - row {n}: {', '.join(reasons)} — types_raw={raw_types} name='{res['name']}' url='{res['url']}'")

    with open(data_out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    main()
