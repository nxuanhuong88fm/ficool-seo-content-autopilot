# Ficool SEO Content Autopilot v1.0

A structured, draft-first SEO content production system for Ficool's Vietnamese local HVAC/refrigeration website.

## Pipeline

GSC / research → keyword opportunity → funnel → SERP/content gap → brief → article → internal links → image plan → image generation → image SEO → assembly → Local SEO → GEO → conversion → QA → WordPress draft.

## Quick start

```bash
python3 scripts/validate_repo.py
python3 scripts/ficool.py demo "máy lạnh bị chảy nước"
pytest -q
```

The demo uses a mock image provider and creates artifacts under `output/`. Production connectors are intentionally credential-driven and draft-first.

## Repository design

- `config/`: site, brand, services, SEO, images and WordPress policy.
- `knowledge/`: Ficool-specific editorial and business context.
- `skills/`: agent contracts and responsibilities.
- `workflows/`: orchestration definitions.
- `schemas/`: structured artifact contracts.
- `connectors/`: external integrations and provider abstractions.
- `scripts/`: CLI and deterministic validation.

## Safety

Do not commit `.env` or credentials. Do not fabricate claims. Review generated content before production publishing.
