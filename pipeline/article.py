from __future__ import annotations
import os,json
from openai import OpenAI
from pipeline.utils import dump_yaml,slugify
class ArticlePipeline:
    def __init__(self):
        key=os.getenv('OPENAI_API_KEY','')
        if not key: raise RuntimeError('OPENAI_API_KEY is required')
        self.client=OpenAI(api_key=key); self.model=os.getenv('OPENAI_TEXT_MODEL','gpt-5.6-luna')
    def run(self,topic,research,output_dir):
        prompt=("Write a Vietnamese Ficool SEO article from the supplied topic/research. Answer the query early; use H2/H3, short paragraphs, useful checklists, FAQ and a funnel-appropriate CTA. "
        "Never invent Ficool prices, warranty, staff, years, certifications, testimonials or statistics. Add image comments like <!-- IMAGE: IMG-001 --> and internal-link comments like <!-- INTERNAL: anchor | /url/ -->. Return article text only.\n"
        f"TOPIC={json.dumps(topic,ensure_ascii=False)}\nRESEARCH={json.dumps(research,ensure_ascii=False)[:30000]}")
        r=self.client.responses.create(model=self.model,input=prompt,store=False); body=r.output_text.strip()
        mr=self.client.responses.create(model=self.model,input='Return JSON only: title<=60 chars, meta_description<=160 chars, slug, secondary_keywords, faq.\n'+body[:18000],store=False)
        try: meta=json.loads(mr.output_text)
        except Exception: meta={'title':topic['title'],'meta_description':topic['title'],'slug':slugify(topic['title']),'secondary_keywords':topic['secondary_keywords'],'faq':[]}
        dump_yaml(output_dir/'article-draft.yaml',{'topic':topic,'article':body,'seo':meta}); (output_dir/'article.md').write_text(body,encoding='utf-8')
        return {'title':meta.get('title') or topic['title'],'body':body,'seo':meta,'slug':meta.get('slug') or slugify(topic['title'])}
