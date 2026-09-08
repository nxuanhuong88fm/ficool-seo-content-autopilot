from __future__ import annotations
import hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOPICS=ROOT/'knowledge/seo/topic-seed.json'
MANIFEST_DIR=ROOT/'output/manifests'

def slugify(s):
    s=s.lower().strip(); s=re.sub(r'[^\w\s-]','',s,flags=re.UNICODE); return re.sub(r'[-\s]+','-',s).strip('-')

def load_topics():
    data=json.loads(TOPICS.read_text(encoding='utf-8')); return [(cat,t) for cat,items in data.items() for t in items]

def load_manifests():
    seen=set()
    MANIFEST_DIR.mkdir(parents=True,exist_ok=True)
    for p in MANIFEST_DIR.glob('*.json'):
        try:
            d=json.loads(p.read_text(encoding='utf-8')); seen.update(x for x in (d.get('topic'),d.get('slug'),d.get('wp_slug')) if x)
        except Exception: pass
    return seen

def score(topic, rows):
    q=topic.lower(); score=0.0
    for r in rows:
        text=str(r.get('query','')).lower()
        if q in text or text in q:
            score += float(r.get('impressions',0))*0.02 + float(r.get('clicks',0))*2 + max(0,20-float(r.get('position',20)))
    return score

def choose_topic(rows):
    seen=load_manifests(); candidates=[]
    for cat,topic in load_topics():
        slug=slugify(topic)
        if topic in seen or slug in seen: continue
        candidates.append((score(topic,rows),cat,topic,slug))
    if not candidates: raise SystemExit('No unprocessed topic remains.')
    candidates.sort(reverse=True)
    return candidates[0]

def run():
    from connectors.gsc.client import GSCClient
    gsc=GSCClient()
    rows=gsc.last_n_days(int(os.getenv('GSC_LOOKBACK_DAYS','90')),dimensions=['query','page'])
    score_value,category,topic,slug=choose_topic(rows)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+hashlib.sha1(topic.encode()).hexdigest()[:8]
    out=ROOT/'output/runs'/run_id; out.mkdir(parents=True,exist_ok=True)
    (out/'selection.json').write_text(json.dumps({'topic':topic,'category':category,'slug':slug,'gsc_score':score_value,'selected_at':datetime.now(timezone.utc).isoformat()},ensure_ascii=False,indent=2),encoding='utf-8')
    # Production orchestration hooks. Each stage must be implemented by the corresponding connector/skill.
    from connectors.web_search.serper import SerperClient
    serp=SerperClient().compact(topic)
    (out/'serp.json').write_text(json.dumps(serp,ensure_ascii=False,indent=2),encoding='utf-8')
    from connectors.web_search.openai_research import OpenAIResearchClient
    research=OpenAIResearchClient().research(f'Vietnamese SEO research for Ficool topic: {topic}. Use the SERP context and authoritative sources. Return evidence, entities, questions, outline recommendations and source URLs. Do not invent facts.')
    (out/'research.json').write_text(json.dumps(research,ensure_ascii=False,indent=2),encoding='utf-8')
    # Article/image generation remains delegated to skills so providers can be swapped without changing orchestration.
    manifest={'run_id':run_id,'topic':topic,'slug':slug,'category':category,'status':'researched','gsc_score':score_value,'created_at':datetime.now(timezone.utc).isoformat()}
    mp=MANIFEST_DIR/(run_id+'.json'); mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__': run()
