#!/usr/bin/env python3
"""Diagnostic 2: What themes do dropped articles have? What companies appear in .tr financial articles?"""

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
p_start = window_start.strftime("%Y-%m-%d")
p_end = window_end.strftime("%Y-%m-%d")

print(f"=== DIAGNOSTIC 2: {window_start.isoformat()} -> {window_end.isoformat()} ===\n")

# ---- PART 1: What themes do Turkcell articles have? ----
print("--- PART 1: Sample Turkcell .tr articles (no financial filter) ---")
q1 = f"""
SELECT 
  DocumentIdentifier,
  SUBSTR(V2Themes, 1, 300) as themes_sample,
  V2Tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
  AND SourceCommonName LIKE '%.tr'
  AND (
    REGEXP_CONTAINS(LOWER(V2Themes), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(V2Organizations), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(AllNames), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(V2Persons), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(Extras), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'turkcell')
  )
LIMIT 5
"""
for row in client.query(q1).result():
    print(f"  URL: {row.DocumentIdentifier[:100]}")
    print(f"  Themes: {row.themes_sample}")
    print(f"  Tone: {row.V2Tone}")
    print()

# ---- PART 2: What themes do Halkbank articles have? ----
print("--- PART 2: Sample Halkbank .tr articles (no financial filter) ---")
q2 = f"""
SELECT 
  DocumentIdentifier,
  SUBSTR(V2Themes, 1, 300) as themes_sample,
  V2Tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
  AND SourceCommonName LIKE '%.tr'
  AND (
    REGEXP_CONTAINS(LOWER(V2Themes), r'halkbank')
    OR REGEXP_CONTAINS(LOWER(V2Organizations), r'halkbank')
    OR REGEXP_CONTAINS(LOWER(AllNames), r'halkbank')
    OR REGEXP_CONTAINS(LOWER(V2Persons), r'halkbank')
    OR REGEXP_CONTAINS(LOWER(Extras), r'halkbank')
    OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'halkbank')
  )
LIMIT 5
"""
for row in client.query(q2).result():
    print(f"  URL: {row.DocumentIdentifier[:100]}")
    print(f"  Themes: {row.themes_sample}")
    print(f"  Tone: {row.V2Tone}")
    print()

# ---- PART 3: Sample of .tr financial articles — what companies do they mention? ----
print("--- PART 3: Top organizations in .tr financial articles ---")
q3 = f"""
SELECT 
  org,
  COUNT(*) as cnt
FROM (
  SELECT 
    REGEXP_EXTRACT(V2Organizations, r'([^;]+)') as org
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
    AND SourceCommonName LIKE '%.tr'
    AND REGEXP_CONTAINS(LOWER(V2Themes), r'{FINANCIAL_THEME_FILTER}')
    AND V2Organizations IS NOT NULL
)
WHERE org IS NOT NULL AND LENGTH(org) > 2
GROUP BY org
ORDER BY cnt DESC
LIMIT 30
"""
for row in client.query(q3).result():
    print(f"  {row.cnt:4d}  {row.org}")

# ---- PART 4: Sample URLs from .tr financial articles ----
print("\n--- PART 4: Sample .tr financial article URLs ---")
q4 = f"""
SELECT DocumentIdentifier, SUBSTR(V2Tone, 1, 20) as tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
  AND SourceCommonName LIKE '%.tr'
  AND REGEXP_CONTAINS(LOWER(V2Themes), r'{FINANCIAL_THEME_FILTER}')
LIMIT 10
"""
for row in client.query(q4).result():
    print(f"  {row.DocumentIdentifier[:120]}")

# ---- PART 5: What fields contain company names? ----
print("\n--- PART 5: Where does 'turkcell' appear in matched articles? ---")
q5 = f"""
SELECT 
  REGEXP_CONTAINS(LOWER(V2Themes), r'turkcell') as in_themes,
  REGEXP_CONTAINS(LOWER(V2Organizations), r'turkcell') as in_orgs,
  REGEXP_CONTAINS(LOWER(AllNames), r'turkcell') as in_allnames,
  REGEXP_CONTAINS(LOWER(V2Persons), r'turkcell') as in_persons,
  REGEXP_CONTAINS(LOWER(Extras), r'turkcell') as in_extras,
  REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'turkcell') as in_url,
  COUNT(*) as cnt
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE(_PARTITIONTIME) BETWEEN '{p_start}' AND '{p_end}'
  AND SourceCommonName LIKE '%.tr'
  AND (
    REGEXP_CONTAINS(LOWER(V2Themes), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(V2Organizations), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(AllNames), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(V2Persons), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(Extras), r'turkcell')
    OR REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'turkcell')
  )
GROUP BY 1,2,3,4,5,6
ORDER BY cnt DESC
"""
for row in client.query(q5).result():
    fields = []
    if row.in_themes: fields.append("V2Themes")
    if row.in_orgs: fields.append("V2Orgs")
    if row.in_allnames: fields.append("AllNames")
    if row.in_persons: fields.append("V2Persons")
    if row.in_extras: fields.append("Extras")
    if row.in_url: fields.append("URL")
    print(f"  {row.cnt:3d} articles: found in {', '.join(fields)}")
