from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml",
    "config/site.yaml", "config/brand.yaml", "config/services.yaml",
    "config/images.yaml", "workflows/create-article.yaml",
    "skills/blog-writer/SKILL.md", "skills/image-planner/SKILL.md",
    "skills/image-generator/SKILL.md", "skills/image-seo/SKILL.md",
    "skills/content-assembler/SKILL.md", "skills/content-qa/SKILL.md",
    "skills/wordpress-publisher/SKILL.md", "connectors/wordpress/client.py",
    "connectors/image_provider/provider.py", "schemas/brief.schema.yaml",
    "schemas/image-manifest.schema.yaml", "tests/test_demo.py",
]
missing = [p for p in REQUIRED if not (ROOT / p).exists()]
if missing:
    raise SystemExit("Missing files:\n" + "\n".join(missing))
print(f"OK: {len(REQUIRED)} required files present.")
