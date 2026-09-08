# Ficool SEO Content Autopilot v1.1 Production

Production-oriented AI SEO content automation for Ficool, a local HVAC/refrigeration service in Ho Chi Minh City.

## Production pipeline

**GSC → 108 Ficool topics → GSC prioritization → SERP → AI web research → AI article → real image generation → WordPress Media → contextual image insertion → SEO/GEO/Local QA → WordPress Draft**.

The repository now contains production adapters for Google Search Console Search Analytics, Serper SERP, OpenAI Responses web research, OpenAI image generation and WordPress REST API. WordPress remains Draft-first.

## 108 topics

`knowledge/seo/topic-seed.json` is the canonical 108-topic seed: 6 categories × 18 topics. `pipeline/topic_selector.py` derives the structured topic contract used by downstream agents.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Configure `OPENAI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS` + `GSC_SITE_URL`, `SERPER_API_KEY`, and the WordPress variables. Grant the Google service-account email access to the Search Console property. Use a WordPress Application Password over HTTPS.

## Commands

```bash
python scripts/validate_repo.py
python scripts/ficool.py topics
python scripts/ficool.py show ML-01
python scripts/ficool.py run ML-01 --mock-images
python scripts/ficool.py run ML-01
```

`--mock-images` is only for smoke tests. A production run uses the real image provider. QA failure blocks WordPress Draft creation. No automatic publish path exists.

## Run artifacts

Each run stores research, GSC/SERP evidence, article draft, image manifest, assembled HTML, QA and WordPress results under `output/runs/<topic>-<run-id>/`.
