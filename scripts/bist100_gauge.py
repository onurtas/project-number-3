# ============================================================
# BIST100 News Sentiment — Duygu Göstergesi (Gauge)
# Dual Speedometer: Turkey (top) + International/G20 (bottom)
#
# 24h window, no baselines
# 3-layer content filtering:
#   L1: V2Themes financial filter (SQL)
#   L2: BIST/ticker co-occurrence for ambiguous (SQL)
#   L3: Tone winsorization + min articles (Python)
#
# 20 gauge keywords: 5 generic BIST terms + 15 blue-chip companies
# Two-stage aggregation: AVG per keyword → AVG of averages
# Scale: -10 to +10
# Project: gdelt-research-470509
# ============================================================

# ---------- 0) SETTINGS ----------
from datetime import datetime, timedelta, timezone

NOW_UTC = datetime(2026, 3, 1, 18, 0, tzinfo=timezone.utc)  # manual override for testing
# NOW_UTC = datetime.now(timezone.utc)  # production mode

WINDOW_HOURS = 24
MIN_ARTICLES_TOTAL = 30
MIN_ARTICLES_PER_KW = 3
TONE_WINSORIZE = 15  # cap extreme tones at ±15

# Time windows
window_start = NOW_UTC - timedelta(hours=WINDOW_HOURS)
window_end = NOW_UTC

# Partition range (may span 2 calendar days)
partition_start = window_start.strftime("%Y-%m-%d")
partition_end = window_end.strftime("%Y-%m-%d")

# Timestamps for precise filtering within partitions
window_start_ts = window_start.strftime("%Y%m%d%H%M%S")
window_end_ts = window_end.strftime("%Y%m%d%H%M%S")

print(f"24h window: {window_start.isoformat()} -> {window_end.isoformat()}")
print(f"Partition range: {partition_start} -> {partition_end}")

# ---------- 1) SETUP ----------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from google.cloud import bigquery
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from auth_helper import get_bq_client, PROJECT_ID, REGION
from bist100_config import (
    GAUGE_KEYWORDS, G20_COUNTRIES, SCOPE_LABELS,
    FINANCIAL_THEME_FILTER, DISCLAIMER, TWEET_HASHTAGS,
    CHART_TITLE_GAUGE
)
import pathlib

AUX_DATASET = "gdelt_aux"
LOOKUP_TABLE = "source_domain_country"
LOOKUP_FQN = f"{PROJECT_ID}.{AUX_DATASET}.{LOOKUP_TABLE}"

client = get_bq_client()

# ---------- 2) ENSURE DATASET + UPLOAD DOMAIN LOOKUP ----------
full_dataset_id = f"{PROJECT_ID}.{AUX_DATASET}"
try:
    client.get_dataset(full_dataset_id)
except Exception:
    ds = bigquery.Dataset(full_dataset_id)
    ds.location = REGION
    client.create_dataset(ds)
    print(f"Created dataset: {full_dataset_id}")

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

# ---------- 3) BUILD KEYWORD SQL ----------
kw_rows_sql = ",\n    ".join(
    [f"STRUCT('{k['label']}' AS label, r\"{k['pattern']}\" AS pattern)"
     for k in GAUGE_KEYWORDS]
)

# G20 country list for SQL
g20_sql = ", ".join([f"'{c}'" for c in G20_COUNTRIES])

# ---------- 4) BIGQUERY ----------
sql = f"""
WITH lkp AS (
  SELECT domain, countrycode
  FROM `{LOOKUP_FQN}`
),
g AS (
  SELECT
    SUBSTR(GKGRECORDID, 1, 14) AS record_ts,
    NET.REG_DOMAIN(DocumentIdentifier) AS domain,
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
filtered AS (
  SELECT *
  FROM g
  WHERE record_ts BETWEEN '{window_start_ts}' AND '{window_end_ts}'
    AND tone_val IS NOT NULL
    AND tone_val BETWEEN -{TONE_WINSORIZE} AND {TONE_WINSORIZE}
    AND REGEXP_CONTAINS(themes_lower, r'{FINANCIAL_THEME_FILTER}')
),
kw AS (
  SELECT * FROM UNNEST([
    {kw_rows_sql}
  ])
),
hits AS (
  SELECT
    kw.label, f.tone_val, f.record_ts, f.domain
  FROM filtered f
  JOIN kw ON REGEXP_CONTAINS(f.text_all, kw.pattern)
),
tr_agg AS (
  SELECT
    h.label, 'TR' AS scope,
    AVG(h.tone_val) AS tone_avg,
    COUNT(*) AS n_articles
  FROM hits h
  JOIN lkp ON h.domain = lkp.domain
  WHERE lkp.countrycode = 'TR'
  GROUP BY h.label
),
g20_agg AS (
  SELECT
    h.label, 'G20' AS scope,
    AVG(h.tone_val) AS tone_avg,
    COUNT(*) AS n_articles
  FROM hits h
  JOIN lkp ON h.domain = lkp.domain
  WHERE lkp.countrycode IN ({g20_sql})
  GROUP BY h.label
)
SELECT * FROM tr_agg
UNION ALL
SELECT * FROM g20_agg
ORDER BY scope, label
"""

print("Running BigQuery (24h window, financial theme filter)...")
print(f"Scanning partitions: {partition_start} to {partition_end}")
df_raw = client.query(sql).to_dataframe()
print(f"Query returned {len(df_raw)} rows")

if df_raw.empty:
    print("WARNING: No data returned. Check date range and filters.")

# ---------- 5) TWO-STAGE AGGREGATION ----------
def compute_gauge(df, scope):
    """Two-stage: AVG(tone) per keyword → AVG of keyword averages."""
    subset = df[df["scope"] == scope].copy()
    n_total = int(subset["n_articles"].sum())

    # Only include keywords with enough articles
    valid = subset[subset["n_articles"] >= MIN_ARTICLES_PER_KW]
    gauge_value = valid["tone_avg"].mean() if len(valid) > 0 else np.nan

    return {
        "scope": scope,
        "current": round(gauge_value, 2) if not np.isnan(gauge_value) else None,
        "n_articles": n_total,
        "n_keywords": len(valid),
        "n_keywords_total": len(subset),
    }

print("\nComputing gauges...")
gauge_tr = compute_gauge(df_raw, "TR")
gauge_g20 = compute_gauge(df_raw, "G20")

print("\n" + "=" * 50)
print("GAUGE RESULTS")
print("=" * 50)
for g in [gauge_tr, gauge_g20]:
    label = SCOPE_LABELS.get(g["scope"], g["scope"])
    print(f"\n{label} ({g['scope']}):")
    print(f"  Current: {g['current']}  ({g['n_articles']} articles, {g['n_keywords']}/{g['n_keywords_total']} keywords)")

# ---------- 6) SPEEDOMETER CHART ----------
def draw_speedometer(ax, value, scope_label, n_articles):
    """
    Clean half-circle speedometer.
    Shows current 24h sentiment value — no baselines.
    """
    val = np.clip(value, -10, 10) if value is not None else 0

    center_x, center_y = 0.5, 0.38
    radius_outer = 0.36
    radius_inner = 0.25

    def val_to_angle(v):
        frac = (v - (-10)) / 20.0
        return 180 - frac * 180

    def angle_to_xy(angle_deg, r):
        rad = np.radians(angle_deg)
        return center_x + r * np.cos(rad), center_y + r * np.sin(rad)

    # --- Colored arc zones ---
    zones = [
        (-10, -3, "#EF4444"),   # Red - Düşüş
        (-3,  -1, "#F97316"),   # Orange - Hafif Düşüş
        (-1,   1, "#FBBF24"),   # Yellow - Nötr
        ( 1,   3, "#34D399"),   # Light Green - Hafif Yükseliş
        ( 3,  10, "#22C55E"),   # Green - Yükseliş
    ]
    for z_min, z_max, color in zones:
        a1, a2 = val_to_angle(z_min), val_to_angle(z_max)
        theta1, theta2 = min(a1, a2), max(a1, a2)
        n_pts = 60
        angles = np.linspace(np.radians(theta2), np.radians(theta1), n_pts)
        x_o = center_x + radius_outer * np.cos(angles)
        y_o = center_y + radius_outer * np.sin(angles)
        x_i = center_x + radius_inner * np.cos(angles[::-1])
        y_i = center_y + radius_inner * np.sin(angles[::-1])
        ax.fill(np.concatenate([x_o, x_i]), np.concatenate([y_o, y_i]),
                color=color, alpha=0.85)

    # --- Major tick marks ---
    for tv, tl in zip([-10, -5, 0, 5, 10], ["-10", "-5", "0", "+5", "+10"]):
        a = val_to_angle(tv)
        x1, y1 = angle_to_xy(a, radius_outer)
        x2, y2 = angle_to_xy(a, radius_outer + 0.018)
        ax.plot([x1, x2], [y1, y2], color="#374151", linewidth=1.5)
        xl, yl = angle_to_xy(a, radius_outer + 0.04)
        ax.text(xl, yl, tl, ha="center", va="center", fontsize=9,
                color="#374151", fontweight="bold")

    # Minor ticks
    for tv in range(-9, 10):
        if tv not in [-10, -5, 0, 5, 10]:
            a = val_to_angle(tv)
            x1, y1 = angle_to_xy(a, radius_outer)
            x2, y2 = angle_to_xy(a, radius_outer + 0.01)
            ax.plot([x1, x2], [y1, y2], color="#9CA3AF", linewidth=0.7)

    # --- Edge labels ---
    ax.text(center_x - radius_outer - 0.02, center_y - 0.04, "Düşüş",
            ha="center", va="top", fontsize=8, color="#DC2626", fontweight="bold")
    ax.text(center_x + radius_outer + 0.02, center_y - 0.04, "Yükseliş",
            ha="center", va="top", fontsize=8, color="#16A34A", fontweight="bold")

    # --- Needle ---
    if value is not None:
        na = val_to_angle(val)
        nr = np.radians(na)
        nl = radius_inner - 0.015
        bw = 0.011
        tx = center_x + nl * np.cos(nr)
        ty = center_y + nl * np.sin(nr)
        lx = center_x + bw * np.cos(nr + np.pi / 2)
        ly = center_y + bw * np.sin(nr + np.pi / 2)
        rx = center_x + bw * np.cos(nr - np.pi / 2)
        ry = center_y + bw * np.sin(nr - np.pi / 2)
        tail = 0.025
        tlx = center_x - tail * np.cos(nr)
        tly = center_y - tail * np.sin(nr)
        ax.fill([tx, lx, tlx, rx], [ty, ly, tly, ry], color="#1F2937", zorder=5)
        ax.add_patch(plt.Circle((center_x, center_y), 0.020, color="#1F2937", zorder=6))
        ax.add_patch(plt.Circle((center_x, center_y), 0.009, color="#E5E7EB", zorder=7))

    # --- Value color + sentiment label ---
    if value is None:
        vc, lt = "#9CA3AF", "Veri Yok"
    elif val <= -3:
        vc, lt = "#DC2626", "Düşüş"
    elif val <= -1:
        vc, lt = "#EA580C", "Hafif Düşüş"
    elif val <= 1:
        vc, lt = "#D97706", "Nötr"
    elif val <= 3:
        vc, lt = "#059669", "Hafif Yükseliş"
    else:
        vc, lt = "#16A34A", "Yükseliş"

    # --- TEXT LAYOUT ---

    # Scope title ABOVE gauge
    ax.text(center_x, center_y + radius_outer + 0.08, scope_label,
            ha="center", va="center", fontsize=15, fontweight="bold", color="#111827")

    # Big value number
    if value is not None:
        ax.text(center_x, center_y - 0.06, f"{value:+.2f}",
                ha="center", va="center", fontsize=30, fontweight="bold", color=vc)
    else:
        ax.text(center_x, center_y - 0.06, "N/A",
                ha="center", va="center", fontsize=26, color="#9CA3AF")

    # Sentiment label
    ax.text(center_x, center_y - 0.14, f"{lt}",
            ha="center", va="center", fontsize=11, fontweight="bold", color=vc)

    # Article count
    ax.text(center_x, center_y - 0.22,
            f"{n_articles:,} haber analiz edildi",
            ha="center", va="center", fontsize=9, color="#6B7280")

    # Axis limits
    m = 0.06
    ax.set_xlim(0 - m, 1 + m)
    ax.set_ylim(center_y - 0.30, center_y + radius_outer + 0.14)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------- 7) CREATE FIGURE ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 11.5))

# Title (bold) and subtitle (lighter) with clear separation
fig.suptitle(CHART_TITLE_GAUGE,
             fontsize=20, fontweight="bold", color="#111827", y=0.97)
fig.text(0.5, 0.935,
         f"{window_end.strftime('%d.%m.%Y %H:%M')} UTC  ·  son 24 saat",
         ha="center", fontsize=11, color="#6B7280")

# Turkey gauge (top)
draw_speedometer(ax1,
    value=gauge_tr["current"],
    scope_label=SCOPE_LABELS["TR"],
    n_articles=gauge_tr["n_articles"],
)

# G20 gauge (bottom)
draw_speedometer(ax2,
    value=gauge_g20["current"],
    scope_label=SCOPE_LABELS["G20"],
    n_articles=gauge_g20["n_articles"],
)

# Disclaimer footer
fig.text(0.5, 0.015, DISCLAIMER,
         ha="center", fontsize=8, color="#9CA3AF")

plt.tight_layout(rect=[0, 0.03, 1, 0.92])

# Save
OUTDIR = pathlib.Path("gdelt_bq_results"); OUTDIR.mkdir(exist_ok=True)
tag = window_end.strftime("%Y%m%d_%H%M")
png_path = OUTDIR / f"bist100_gauge_{tag}.png"
plt.savefig(png_path, dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print(f"\nSaved: {png_path}")

# ---------- 8) SAVE JSON ----------
import json
gauge_data = {
    "timestamp": window_end.isoformat(),
    "window_hours": WINDOW_HOURS,
    "min_articles_total": MIN_ARTICLES_TOTAL,
    "min_articles_per_keyword": MIN_ARTICLES_PER_KW,
    "tone_winsorize": TONE_WINSORIZE,
    "fields_searched": "V2Themes + V2Persons + V2Organizations + AllNames + Extras + DocumentIdentifier",
    "financial_theme_filter": "Layer 1 applied",
    "turkey": gauge_tr,
    "g20": gauge_g20,
    "g20_countries": G20_COUNTRIES,
    "per_keyword": df_raw.to_dict(orient="records")
}
json_path = OUTDIR / f"bist100_gauge_{tag}.json"
with open(json_path, "w") as f:
    json.dump(gauge_data, f, indent=2, default=str)
print(f"Saved: {json_path}")

# ---------- 9) TWEET TEXT ----------
def format_tweet(gauge_tr, gauge_g20, window_end):
    def tone_label(val):
        if val is None: return "Veri Yok"
        if val <= -3: return "Düşüş"
        if val <= -1: return "Hafif Düşüş"
        if val <= 1: return "Nötr"
        if val <= 3: return "Hafif Yükseliş"
        return "Yükseliş"

    def fv(v):
        return f"{v:+.2f}" if v is not None else "N/A"

    tr, g = gauge_tr, gauge_g20
    return (
        f"{CHART_TITLE_GAUGE}\n"
        f"{window_end.strftime('%d.%m.%Y %H:%M')} UTC\n\n"
        f"{SCOPE_LABELS['TR']}: {fv(tr['current'])} ({tone_label(tr['current'])})\n"
        f"  {tr['n_articles']:,} haber analiz edildi\n\n"
        f"{SCOPE_LABELS['G20']}: {fv(g['current'])} ({tone_label(g['current'])})\n"
        f"  {g['n_articles']:,} haber analiz edildi\n\n"
        f"{DISCLAIMER}\n"
        f"{TWEET_HASHTAGS}"
    )

tweet_text = format_tweet(gauge_tr, gauge_g20, window_end)
print("\n" + "=" * 50)
print("TWEET PREVIEW")
print("=" * 50)
print(tweet_text)
print(f"\nCharacter count: {len(tweet_text)}")

# ---------- 10) SAVE POST METADATA ----------
post_meta = {
    "tweet_text": tweet_text,
    "png_path": str(png_path),
}
post_path = OUTDIR / f"bist100_gauge_{tag}_post.json"
with open(post_path, "w") as f:
    json.dump(post_meta, f, indent=2, ensure_ascii=False)
print(f"Saved: {post_path}")
