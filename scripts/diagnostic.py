#!/usr/bin/env python3
"""Diagnostic: check article coverage for gauge keywords (generic + blue-chip)"""

import json, os, sys
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
sys.path.insert(0, os.path.dirname(__file__))
from bist100_config import (BIST100_COMPANIES, FINANCIAL_THEME_FILTER,
                            GAUGE_GENERIC_KEYWORDS, GAUGE_BLUECHIP_TICKERS)
from auth_helper import get_bq_client

client = get_bq_client()
NOW_UTC = datetime.now(timezone.utc)
window_start = NOW_UTC - timedelta(hours=24)
window_end = NOW_UTC
p_start = window_start.strftime("%Y-%m-%d")
p_end = window_end.strftime("%Y-%m-%d")

print(f"Diagnostic: {window_start.isoformat()} -> {window_end.isoformat()}")
print()

def count_articles(pattern, scope_filter):
    q = f"""
    SELECT COUNT(*) as cnt
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
      {scope_filter}
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
    return list(client.query(q).result())[0].cnt

def count_no_filter(pattern, scope_filter):
    q = f"""
    SELECT COUNT(*) as cnt
    FROM `gdelt-bq.gdeltv2.gkg_partitioned`
    WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
      {scope_filter}
      AND (
        REGEXP_CONTAINS(LOWER(V2Themes), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Organizations), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(AllNames), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(V2Persons), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(Extras), r'{pattern}')
        OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'{pattern}')
      )
    """
    return list(client.query(q).result())[0].cnt

TR_FILTER = "AND SourceCommonName LIKE '%.tr'"

print("=== GENERIC KEYWORDS — Turkey (.tr) ===")
tr_total = 0
for kw in GAUGE_GENERIC_KEYWORDS:
    try:
        no_f = count_no_filter(kw["pattern"], TR_FILTER)
        with_f = count_articles(kw["pattern"], TR_FILTER)
        pct = f"({with_f/no_f*100:.0f}%)" if no_f > 0 else ""
        print(f"  {kw['label']:20s}  no_filter: {no_f:4d}  with_filter: {with_f:4d}  {pct}")
        tr_total += with_f
    except Exception as e:
        print(f"  {kw['label']:20s}  ERROR: {e}")
print(f"  {'TOTAL':20s}  with_filter: {tr_total:4d}")

print("\n=== BLUE-CHIP COMPANIES — Turkey (.tr) ===")
for ticker in GAUGE_BLUECHIP_TICKERS:
    c = next((x for x in BIST100_COMPANIES if x["ticker"] == ticker), None)
    if not c: continue
    try:
        no_f = count_no_filter(c["pattern"], TR_FILTER)
        with_f = count_articles(c["pattern"], TR_FILTER)
        pct = f"({with_f/no_f*100:.0f}%)" if no_f > 0 else ""
        flag = " ⚠️" if no_f > 0 and with_f == 0 else ""
        print(f"  {c['label']:20s}  no_filter: {no_f:4d}  with_filter: {with_f:4d}  {pct}{flag}")
    except Exception as e:
        print(f"  {c['label']:20s}  ERROR: {e}")

print("\n=== BLUE-CHIP COMPANIES — International (non-.tr) ===")
INTL_FILTER = "AND SourceCommonName NOT LIKE '%.tr'"
for ticker in GAUGE_BLUECHIP_TICKERS:
    c = next((x for x in BIST100_COMPANIES if x["ticker"] == ticker), None)
    if not c: continue
    try:
        with_f = count_articles(c["pattern"], INTL_FILTER)
        if with_f > 0:
            print(f"  {c['label']:20s}  articles: {with_f:4d}")
    except Exception as e:
        print(f"  {c['label']:20s}  ERROR: {e}")

q_total = f"""
SELECT COUNT(*) as cnt
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
  AND SourceCommonName LIKE '%.tr'
  AND REGEXP_CONTAINS(LOWER(V2Themes), r'{FINANCIAL_THEME_FILTER}')
"""
total = list(client.query(q_total).result())[0].cnt
print(f"\n  Total .tr financial articles (24h): {total}")
