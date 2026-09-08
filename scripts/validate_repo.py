from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=['README.md','AGENTS.md','.env.example','pyproject.toml','knowledge/seo/topic-seed.json','connectors/gsc/client.py','connectors/web_search/serper.py','connectors/web_search/openai_research.py','connectors/image_provider/provider.py','connectors/wordpress/client.py','pipeline/run.py','pipeline/prioritize.py','pipeline/topic_selector.py']
missing=[p for p in REQUIRED if not (ROOT/p).exists()]
if missing: raise SystemExit('Missing files:\n'+'\n'.join(missing))
seed=json.loads((ROOT/'knowledge/seo/topic-seed.json').read_text(encoding='utf-8'))
count=sum(len(v) for v in seed.values())
if count!=108 or len(seed)!=6 or any(len(v)!=18 for v in seed.values()): raise SystemExit(f'Expected 6 categories x 18 topics = 108, got {count}')
print(f'OK: {len(REQUIRED)} production files present; 108 topics present.')
