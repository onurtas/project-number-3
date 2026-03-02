#!/usr/bin/env python3
"""Quick diagnostic: how many articles match BIST100 companies WITH and WITHOUT financial filter?"""

import json, os, sys
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
sys.path.insert(0, os.path.dirname(__file__))
from bist100_config import BIST100_COMPANIES, FINANCIAL_THEME_FILTER
from auth_helper import get_bq_client

client = get_bq_client()
NOW_UTC = datetime.now(timezone.utc)
window_start = NOW_UTC - timedelta(hours=24)
window_end = NOW_UTC

print(f"Diagnostic: {window_start.isoformat()} -> {window_end.isoformat()}")
print(f"Companies: {len(BIST100_COMPANIES)}")
print()

# Build pattern for top 15 blue-chips (most likely to have coverage)
test_companies = [
    "THY", "Garanti BBVA", "İş Bankası", "Koç Holding", "Sabancı Holding",
    "Akbank", "Halkbank", "Türk Telekom", "Tüpraş", "Ereğli Demir",
    "Ford Otosan", "Arçelik", "BİM", "Turkcell", "Aselsan"
]

for label in test_companies:
    company = next((c for c in BIST100_COMPANIES if c["label"] == label), None)
    if not company:
        continue
    
    pattern = company["pattern"]
    
    # Query 1: WITHOUT financial filter (TR scope)
    q_no_filter = f"""
    SELECT COUNT(*) as cnt
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE DATE(_PARTITIONTIME) BETWEEN '{window_start.strftime("%Y-%m-%d")}' AND '{window_end.strftime("%Y-%m-%d")}'
      AND SourceCommonName LIKE '%.tr'
      AND (
        REGEXP_CONTAINS(LOWER(V2Themes), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Organizations), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(AllNames), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Persons), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(Extras), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'{pattern}')
      )
    """
    
    # Query 2: WITH financial filter (TR scope)
    q_with_filter = f"""
    SELECT COUNT(*) as cnt
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE DATE(_PARTITIONTIME) BETWEEN '{window_start.strftime("%Y-%m-%d")}' AND '{window_end.strftime("%Y-%m-%d")}'
      AND SourceCommonName LIKE '%.tr'
      AND REGEXP_CONTAINS(LOWER(V2Themes), r'{FINANCIAL_THEME_FILTER}')
      AND (
        REGEXP_CONTAINS(LOWER(V2Themes), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Organizations), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(AllNames), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Persons), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(Extras), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'{pattern}')
      )
    """
    
    try:
        r1 = list(client.query(q_no_filter).result())[0].cnt
        r2 = list(client.query(q_with_filter).result())[0].cnt
        pct = f"({r2/r1*100:.0f}%)" if r1 > 0 else ""
        flag = " ⚠️ FILTER DROPS ALL" if r1 > 0 and r2 == 0 else ""
        print(f"  {label:20s}  no_filter: {r1:4d}  with_filter: {r2:4d}  {pct}{flag}")
    except Exception as e:
        print(f"  {label:20s}  ERROR: {e}")

# Also check: how many .tr articles exist at all with financial themes?
q_total = f"""
SELECT COUNT(*) as cnt
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{window_start.strftime("%Y-%m-%d")}' AND '{window_end.strftime("%Y-%m-%d")}'
  AND SourceCommonName LIKE '%.tr'
  AND REGEXP_CONTAINS(LOWER(V2Themes), r'{FINANCIAL_THEME_FILTER}')
"""
total = list(client.query(q_total).result())[0].cnt
print(f"\n  Total .tr financial articles (24h): {total}")
