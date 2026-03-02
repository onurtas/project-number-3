# BIST100 News Sentiment Platform

Automated BIST100 stock news sentiment analysis using GDELT data, publishing to X (Twitter).

## 6 Daily Posts

| Time (UTC) | Post | Scope |
|------------|------|-------|
| 07:00 | Dual Speedometer | Turkey + International |
| 10:00 | Top 10 Positive | Turkey |
| 13:00 | Top 10 Negative | Turkey |
| 16:00 | Top 10 Positive | International (US, GB, DE, FR, JP, CN) |
| 19:00 | Top 10 Negative | International |
| 22:00 | Dual Speedometer | Turkey + International |

## 3-Layer Content Filtering

1. **Financial theme filter** — V2Themes must contain financial/economic terms
2. **BIST/ticker co-occurrence** — Ambiguous companies require BIST context
3. **Statistical cleanup** — Tone winsorization, min article thresholds

## Setup

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | Google Cloud service account key (BigQuery access) |
| `TWITTER_API_KEY` | X API key |
| `TWITTER_API_SECRET` | X API secret |
| `TWITTER_ACCESS_TOKEN` | X access token |
| `TWITTER_ACCESS_SECRET` | X access token secret |

### Test

Run the `TEST — BigQuery Live Test` workflow manually to validate BigQuery queries before enabling scheduled posts.

## Scripts

- `bist100_config.py` — 100 companies, keywords, filters, settings
- `bist100_gauge.py` — Dual speedometer (Posts 1 & 6)
- `bist100_ranking.py` — Parameterized rankings (Posts 2–5)
- `auth_helper.py` — BigQuery authentication
- `twitter_poster.py` — X posting helper

## Cost

- **Standalone:** $0/month (within BigQuery free tier)
- **Combined with crypto platform:** $8–10/month
