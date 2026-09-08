from __future__ import annotations
import hashlib,json,os,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; TOPICS=ROOT/'knowledge/seo/topic-seed.json'; MANIFEST_DIR=ROOT/'output/manifests'
def slugify(s): return re.sub(r'[-\s]+','-',re.sub(r'[^\w\s-]','',s.lower(),flags=re.UNICODE)).strip('-')
def load_topics():
 d=json.loads(TOPICS.read_text(encoding='utf-8')); return [(c,t) for c,items in d.items() for t in items]
def seen_topics():
 seen=set(); MANIFEST_DIR.mkdir(parents=True,exist_ok=True)
 for p in MANIFEST_DIR.glob('*.json'):
  try:
   d=json.loads(p.read_text(encoding='utf-8')); seen.update(x for x in (d.get('topic'),d.get('slug'),d.get('wp_slug')) if x)
  except Exception: pass
 return seen
def score(topic,rows):
 q=topic.lower(); s=0
 for r in rows:
  x=str(r.get('query','')).lower()
  if q in x or x in q: s+=float(r.get('impressions',0))*.02+float(r.get('clicks',0))*2+max(0,20-float(r.get('position',20)))
 return s
def choose(rows):
 seen=seen_topics(); c=[(score(t,rows),cat,t,slugify(t)) for cat,t in load_topics() if t not in seen and slugify(t) not in seen]
 if not c: raise SystemExit('No unprocessed topic remains.')
 return max(c)
def research_and_write(topic,serp):
 from connectors.web_search.openai_research import OpenAIResearchClient
 prompt=f'''You are Ficool's senior Vietnamese SEO editor. Topic: {topic}. SERP evidence: {json.dumps(serp,ensure_ascii=False)}. Research the topic using web search and write a complete 1400-2200 word Vietnamese article in Markdown. Include a direct answer near the beginning, useful H2/H3 sections, practical troubleshooting boundaries, FAQ, a natural Ho Chi Minh City local-service context, and a soft booking CTA. Do not invent prices, certifications, reviews, statistics, case studies, or business facts. Return ONLY the article Markdown.'''
 return OpenAIResearchClient().research(prompt)['text']
def main():
 from connectors.gsc.client import GSCClient
 rows=GSCClient().last_n_days(int(os.getenv('GSC_LOOKBACK_DAYS','90')),dimensions=['query','page']); gsc_score,cat,topic,slug=choose(rows)
 rid=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+hashlib.sha1(topic.encode()).hexdigest()[:8]; out=ROOT/'output/runs'/rid; out.mkdir(parents=True,exist_ok=True)
 (out/'selection.json').write_text(json.dumps({'topic':topic,'category':cat,'slug':slug,'gsc_score':gsc_score},ensure_ascii=False,indent=2),encoding='utf-8')
 from connectors.web_search.serper import SerperClient
 serp=SerperClient().compact(topic); (out/'serp.json').write_text(json.dumps(serp,ensure_ascii=False,indent=2),encoding='utf-8')
 article=research_and_write(topic,serp); (out/'article.md').write_text(article,encoding='utf-8')
 from connectors.image_provider.provider import OpenAIImageProvider
 provider=OpenAIImageProvider(); image_dir=out/'images'; images=[]
 for i,purpose in enumerate(['featured image showing the device/topic in a realistic Vietnamese home','contextual technical inspection scene related to the main cause'],1):
  p=provider.generate(f'Photorealistic editorial image for a Vietnamese HVAC/refrigeration service article. Topic: {topic}. Purpose: {purpose}. Clean professional service context, realistic equipment, no text, no logos, no watermark.',image_dir/f'{slug}-{i:02d}.png')
  images.append({'id':f'IMG-{i:02d}','path':str(p.relative_to(ROOT)),'alt':f'{topic} - minh họa {purpose}','purpose':purpose})
 from connectors.wordpress.client import WordPressClient
 wp=WordPressClient(); uploaded=[]
 for im in images:
  fp=ROOT/im['path']; mime='image/png'; m=wp.upload_media(fp.read_bytes(),fp.name,mime); im['media_id']=m['id']; im['url']=m.get('source_url',''); uploaded.append(m)
 html='<p>'+article.split('\n\n',1)[0].replace('# ','')+'</p>\n'
 body=article.split('\n\n',1)[1] if '\n\n' in article else article
 for line in body.splitlines():
  if line.startswith('### '): html+=f'<h3>{line[4:]}</h3>\n'
  elif line.startswith('## '): html+=f'<h2>{line[3:]}</h2>\n'
  elif line.strip(): html+=f'<p>{line}</p>\n'
 for im in images: html+=f'<p><img src="{im["url"]}" alt="{im["alt"]}" loading="lazy"></p>\n'
 post=wp.create_post({'title':topic,'slug':slug,'status':'draft','content':html,'featured_media':images[0]['media_id']})
 manifest={'run_id':rid,'topic':topic,'category':cat,'slug':slug,'wp_slug':post.get('slug'),'wp_post_id':post.get('id'),'wp_status':post.get('status'),'gsc_score':gsc_score,'images':images,'created_at':datetime.now(timezone.utc).isoformat()}
 (out/'image-manifest.json').write_text(json.dumps({'article':{'slug':slug},'images':images},ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'wordpress-payload.json').write_text(json.dumps(post,ensure_ascii=False,indent=2),encoding='utf-8')
 (MANIFEST_DIR/(rid+'.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__': main()
