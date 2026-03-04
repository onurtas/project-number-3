# ============================================================
# BIST100 News Sentiment — Haber Duygu Sıralaması (Rankings)
# Single parameterized script for all 4 ranking posts:
#   --scope TR   --direction positive   (Post 2, 10:00 UTC)
#   --scope TR   --direction negative   (Post 3, 13:00 UTC)
#   --scope G20  --direction positive   (Post 4, 16:00 UTC)
#   --scope G20  --direction negative   (Post 5, 19:00 UTC)
#
# 24h window, 100 BIST100 companies (76 safe + 24 ambiguous)
# 3-layer content filtering:
#   L1: V2Themes financial filter (SQL)
#   L2: BIST/ticker co-occurrence for ambiguous (SQL)
#   L3: Tone winsorization + min articles (Python)
# Project: gdelt-research-470509
# ============================================================

# ---------- 0) CLI ARGUMENTS ----------
import argparse

parser = argparse.ArgumentParser(description="BIST100 Ranking Post Generator")
parser.add_argument("--scope", choices=["TR", "G20"], required=True,
                    help="Geographic scope: TR (Turkey) or G20 (6 countries)")
parser.add_argument("--direction", choices=["positive", "negative"], required=True,
                    help="Ranking direction: positive (top 10) or negative (bottom 10)")
args = parser.parse_args()

SCOPE = args.scope
DIRECTION = args.direction

print(f"Generating: {SCOPE} {DIRECTION} ranking")

# ---------- 1) SETTINGS ----------
from datetime import datetime, timedelta, timezone

# NOW_UTC = datetime(2026, 3, 1, 18, 0, tzinfo=timezone.utc)  # manual override for testing
NOW_UTC = datetime.now(timezone.utc)  # production mode

WINDOW_HOURS = 24
TOP_N = 10
MIN_ARTICLES = 3
TONE_WINSORIZE = 15
MIN_COMPANIES_FOR_POST = 3  # skip G20 post if fewer qualify

window_start = NOW_UTC - timedelta(hours=WINDOW_HOURS)
window_end = NOW_UTC

partition_start = window_start.strftime("%Y-%m-%d")
partition_end = window_end.strftime("%Y-%m-%d")
window_start_ts = window_start.strftime("%Y%m%d%H%M%S")
window_end_ts = window_end.strftime("%Y%m%d%H%M%S")

print(f"Window: {window_start.isoformat()} -> {window_end.isoformat()}")

# ---------- 2) SETUP ----------
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from google.cloud import bigquery
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from auth_helper import get_bq_client, PROJECT_ID, REGION
from bist100_config import (
    BIST100_COMPANIES, G20_COUNTRIES, SCOPE_LABELS,
    FINANCIAL_THEME_FILTER, BIST_CONTEXT_BASE,
    get_ambiguous_context_pattern,
    DISCLAIMER, TWEET_HASHTAGS,
    CHART_TITLE_RANKING_POS, CHART_TITLE_RANKING_NEG,
    SINGLE_SOURCE_CAP,
)
import pathlib

AUX_DATASET = "gdelt_aux"
LOOKUP_TABLE = "source_domain_country"
LOOKUP_FQN = f"{PROJECT_ID}.{AUX_DATASET}.{LOOKUP_TABLE}"

client = get_bq_client()

# ---------- 3) UPLOAD DOMAIN LOOKUP ----------
full_dataset_id = f"{PROJECT_ID}.{AUX_DATASET}"
try:
    client.get_dataset(full_dataset_id)
except Exception:
    ds = bigquery.Dataset(full_dataset_id)
    ds.location = REGION
    client.create_dataset(ds)

lookup_url = "https://blog.gdeltproject.org/wp-content/uploads/2021-news-outlets-by-countrycode-2015-2021.csv"
lookup = pd.read_csv(lookup_url)
lookup_top = (
    lookup.sort_values(["domain", "cnt"], ascending=[True, False])
          .groupby("domain", as_index=False)
          .first()
)
job = client.load_table_from_dataframe(
    lookup_top, LOOKUP_FQN,
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
)
job.result()
print(f"Uploaded lookup: {LOOKUP_FQN} ({len(lookup_top)} rows)")

# ---------- 4) BUILD KEYWORD SQL ----------
safe_companies = [c for c in BIST100_COMPANIES if not c["needs_context"]]
ambig_companies = [c for c in BIST100_COMPANIES if c["needs_context"]]

print(f"Companies: {len(safe_companies)} safe + {len(ambig_companies)} ambiguous = {len(BIST100_COMPANIES)}")

safe_kw_sql = ",\n    ".join(
    [f"STRUCT('{c['label']}' AS label, r\"{c['pattern']}\" AS pattern)"
     for c in safe_companies]
)
ambig_kw_sql = ",\n    ".join(
    [f"STRUCT('{c['label']}' AS label, r\"{c['pattern']}\" AS pattern, "
     f"r\"{get_ambiguous_context_pattern(c['ticker'])}\" AS context_pattern)"
     for c in ambig_companies]
)

# Country filter based on scope
if SCOPE == "TR":
    country_filter = "g.source_domain LIKE '%.tr'"
    scope_join = "-- no lookup join for TR scope"
    scope_label_tr = "Türkiye Medyası"
else:
    g20_sql = ", ".join([f"'{c}'" for c in G20_COUNTRIES])
    country_filter = f"lkp.countrycode IN ({g20_sql})"
    scope_join = "JOIN lkp ON g.domain = lkp.domain"
    scope_label_tr = "Uluslararası Medya"

# ---------- 5) BIGQUERY ----------
sql = f"""
WITH lkp AS (
  SELECT domain, countrycode
  FROM `{LOOKUP_FQN}`
),
g AS (
  SELECT
    SUBSTR(GKGRECORDID, 1, 14) AS record_ts,
    NET.REG_DOMAIN(DocumentIdentifier) AS domain,
    SourceCommonName AS source_domain,
    LOWER(CONCAT(
      COALESCE(V2Themes, ''), ' ',
      COALESCE(V2Persons, ''), ' ',
      COALESCE(V2Organizations, ''), ' ',
      COALESCE(AllNames, ''), ' ',
      COALESCE(Extras, ''), ' ',
      COALESCE(DocumentIdentifier, '')
    )) AS text_all,
    LOWER(COALESCE(V2Themes, '')) AS themes_lower,
    CAST(SPLIT(V2Tone, ',')[OFFSET(0)] AS FLOAT64) AS tone_val
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONDATE BETWEEN DATE('{partition_start}') AND DATE('{partition_end}')
),
-- Apply: time window + tone winsorize + financial theme filter (Layer 1) + scope filter
scope_filtered AS (
  SELECT g.text_all, g.tone_val, g.domain
  FROM g
  {scope_join}
  WHERE g.record_ts BETWEEN '{window_start_ts}' AND '{window_end_ts}'
    AND g.tone_val IS NOT NULL
    AND g.tone_val BETWEEN -{TONE_WINSORIZE} AND {TONE_WINSORIZE}
    AND REGEXP_CONTAINS(g.themes_lower, r'{FINANCIAL_THEME_FILTER}')
    AND {country_filter}
),

-- Safe companies: just keyword match
safe_kw AS (
  SELECT * FROM UNNEST([
    {safe_kw_sql}
  ])
),
safe_hits AS (
  SELECT kw.label, f.tone_val, f.domain
  FROM scope_filtered f
  JOIN safe_kw kw ON REGEXP_CONTAINS(f.text_all, kw.pattern)
),

-- Ambiguous companies: keyword match + context filter (Layer 2)
ambig_kw AS (
  SELECT * FROM UNNEST([
    {ambig_kw_sql}
  ])
),
ambig_hits AS (
  SELECT kw.label, f.tone_val, f.domain
  FROM scope_filtered f
  JOIN ambig_kw kw ON REGEXP_CONTAINS(f.text_all, kw.pattern)
  WHERE REGEXP_CONTAINS(f.text_all, kw.context_pattern)
),

all_hits AS (
  SELECT * FROM safe_hits
  UNION ALL
  SELECT * FROM ambig_hits
)

SELECT
  label,
  COUNT(*) AS n_articles,
  AVG(tone_val) AS avg_tone,
  -- For single-source dominance check
  MAX(domain) AS top_domain,
  COUNT(DISTINCT domain) AS n_domains
FROM all_hits
GROUP BY label
ORDER BY avg_tone {"DESC" if DIRECTION == "positive" else "ASC"}
"""

print(f"Running BigQuery ({SCOPE} scope, {WINDOW_HOURS}h, financial filter)...")
df = client.query(sql, location=REGION).to_dataframe()
print(f"Companies with data: {len(df)}")

if not df.empty:
    print(df[["label", "n_articles", "avg_tone"]].to_string(index=False))

# ---------- 6) FILTER + SELECT TOP N ----------
df_qualified = df[df["n_articles"] >= MIN_ARTICLES].copy()
print(f"\nCompanies with >= {MIN_ARTICLES} articles: {len(df_qualified)}")

# Single-source dominance warning (Layer 3)
for idx, row in df_qualified.iterrows():
    if row["n_domains"] == 1 and row["n_articles"] > 1:
        print(f"  ⚠️  {row['label']}: all {int(row['n_articles'])} articles from {row['top_domain']}")

if len(df_qualified) < MIN_COMPANIES_FOR_POST:
    print(f"\nWARNING: Only {len(df_qualified)} companies qualified (need {MIN_COMPANIES_FOR_POST}).")
    print(f"Skipping {SCOPE} {DIRECTION} post — not enough data.")
    # Save skip metadata
    OUTDIR = pathlib.Path("gdelt_bq_results"); OUTDIR.mkdir(exist_ok=True)
    tag = window_end.strftime("%Y%m%d_%H%M")
    skip_meta = {
        "skipped": True,
        "reason": f"Only {len(df_qualified)} companies qualified",
        "scope": SCOPE,
        "direction": DIRECTION,
    }
    skip_path = OUTDIR / f"bist100_ranking_{SCOPE.lower()}_{DIRECTION}_{tag}_post.json"
    with open(skip_path, "w") as f:
        json.dump(skip_meta, f, indent=2)
    print(f"Saved: {skip_path}")
    sys.exit(0)

# Select top N
df_top = df_qualified.head(TOP_N).copy()
total_articles = int(df["n_articles"].sum())
total_qualified = len(df_qualified)

print(f"\nTop {len(df_top)} {DIRECTION}:")
for _, row in df_top.iterrows():
    print(f"  {row['label']:25s}  {int(row['n_articles']):4d} haber  ton: {row['avg_tone']:+.2f}")

# ---------- 7) BAR CHART ----------
if DIRECTION == "positive":
    bar_color = "#22C55E"
    chart_title = CHART_TITLE_RANKING_POS
    df_plot = df_top.sort_values("avg_tone", ascending=True)  # lowest at top → highest at bottom
else:
    bar_color = "#EF4444"
    chart_title = CHART_TITLE_RANKING_NEG
    df_plot = df_top.sort_values("avg_tone", ascending=False)  # highest at top → lowest at bottom

fig, ax = plt.subplots(figsize=(9, 8 if SCOPE == "G20" else 7))

y_pos = range(len(df_plot))
tones = df_plot["avg_tone"].values

bars = ax.barh(y_pos, tones, color=bar_color, height=0.6, edgecolor="white", linewidth=0.5)

# Labels on bars
for bar, (_, row) in zip(bars, df_plot.iterrows()):
    tone = row["avg_tone"]
    n = int(row["n_articles"])
    # Position label at end of bar (outside)
    if DIRECTION == "positive":
        x_pos = tone + 0.08
        ha = "left"
    else:
        x_pos = tone - 0.08
        ha = "right"
    ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
            f"{tone:+.2f}  ({n} haber)",
            ha=ha, va="center", fontsize=9, fontweight="bold", color="#374151")

# Y-axis: company names
ax.set_yticks(y_pos)
ax.set_yticklabels(df_plot["label"], fontsize=11, fontweight="bold", color="#111827")

# Zero line
ax.axvline(x=0, color="#374151", linewidth=0.8, zorder=3)

# X-axis
ax.set_xlabel("Ortalama Ton", fontsize=11, color="#4B5563", fontweight="bold")

# X limits with padding
tone_abs_max = max(abs(tones.min()), abs(tones.max()), 1) * 1.4
if DIRECTION == "positive":
    ax.set_xlim(-0.3, tone_abs_max)
else:
    ax.set_xlim(-tone_abs_max, 0.3)

# Clean up spines
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
ax.tick_params(left=False)
ax.xaxis.grid(True, alpha=0.15, color="#9CA3AF")

# Title and subtitle using fig-level positioning (avoids overlap)
full_title = f"{chart_title} — {scope_label_tr}"
fig.suptitle(full_title, fontsize=16, fontweight="bold", color="#111827", y=0.98)

subtitle_date = f"{window_end.strftime('%d.%m.%Y %H:%M')} UTC  ·  son 24 saat"
if SCOPE == "G20":
    fig.text(0.5, 0.92, subtitle_date, ha="center", fontsize=10, color="#6B7280")
    fig.text(0.5, 0.895, "(ABD, İngiltere, Almanya, Fransa, Japonya, Çin)",
             ha="center", fontsize=9, color="#6B7280")
    rect_top = 0.87
else:
    fig.text(0.5, 0.935, subtitle_date, ha="center", fontsize=10, color="#6B7280")
    rect_top = 0.91

# Summary line
most_extreme = df_top.iloc[0]
summary = (
    f"{most_extreme['label']}, son 24 saatte en {DIRECTION.replace('positive','pozitif').replace('negative','negatif')} "
    f"haberlere sahip ({most_extreme['avg_tone']:+.2f}). "
    f"Toplam {total_qualified} şirket değerlendirildi."
)
fig.text(0.5, 0.03, summary,
         ha="center", fontsize=7.5, color="#6B7280", style="italic")

# Disclaimer
fig.text(0.5, 0.005, DISCLAIMER,
         ha="center", fontsize=7, color="#9CA3AF")

plt.tight_layout(rect=[0, 0.04, 1, rect_top])

# Save
OUTDIR = pathlib.Path("gdelt_bq_results"); OUTDIR.mkdir(exist_ok=True)
tag = window_end.strftime("%Y%m%d_%H%M")
png_path = OUTDIR / f"bist100_ranking_{SCOPE.lower()}_{DIRECTION}_{tag}.png"
plt.savefig(png_path, dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print(f"\nSaved: {png_path}")

# ---------- 8) SAVE JSON ----------
ranking_data = {
    "type": f"ranking_{SCOPE}_{DIRECTION}",
    "timestamp": window_end.isoformat(),
    "window_hours": WINDOW_HOURS,
    "scope": SCOPE,
    "scope_countries": ["TR"] if SCOPE == "TR" else G20_COUNTRIES,
    "direction": DIRECTION,
    "min_articles": MIN_ARTICLES,
    "tone_winsorize": TONE_WINSORIZE,
    "financial_theme_filter": "Layer 1 applied",
    "ambiguous_context_filter": "Layer 2 applied (BIST + ticker)",
    "total_companies_qualified": total_qualified,
    "total_articles": total_articles,
    "top_n": df_top.to_dict(orient="records"),
    "all_companies": df.to_dict(orient="records"),
}
json_path = OUTDIR / f"bist100_ranking_{SCOPE.lower()}_{DIRECTION}_{tag}.json"
with open(json_path, "w") as f:
    json.dump(ranking_data, f, indent=2, default=str)
print(f"Saved: {json_path}")

# ---------- 9) TWEET TEXT ----------
def fv(v): return f"{v:+.2f}" if pd.notna(v) else "N/A"

if DIRECTION == "positive":
    title_tr = f"BIST100 En Pozitif Haberler ({SCOPE_LABELS[SCOPE]})"
else:
    title_tr = f"BIST100 En Negatif Haberler ({SCOPE_LABELS[SCOPE]})"

tweet = (
    f"{title_tr}\n"
    f"{window_end.strftime('%d.%m.%Y %H:%M')} UTC (24sa)\n\n"
)

for i, (_, row) in enumerate(df_top.iterrows(), 1):
    line = f"{i}. {row['label']}: {fv(row['avg_tone'])} ({int(row['n_articles'])} haber)\n"
    if len(tweet) + len(line) + 80 > 280:
        break
    tweet += line

tweet += f"\n{DISCLAIMER}\n{TWEET_HASHTAGS}"

if len(tweet) > 280:
    tweet = tweet[:277] + "..."

print("\n" + "=" * 50)
print("TWEET PREVIEW")
print("=" * 50)
print(tweet)
print(f"\nCharacter count: {len(tweet)}")

# ---------- 10) SAVE POST METADATA ----------
post_meta = {
    "tweet_text": tweet,
    "png_path": str(png_path),
    "skipped": False,
}
post_path = OUTDIR / f"bist100_ranking_{SCOPE.lower()}_{DIRECTION}_{tag}_post.json"
with open(post_path, "w") as f:
    json.dump(post_meta, f, indent=2, ensure_ascii=False)
print(f"Saved: {post_path}")
