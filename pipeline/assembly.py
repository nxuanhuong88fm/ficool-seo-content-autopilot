from __future__ import annotations
import html,re
from markdown import markdown
from pipeline.utils import dump_yaml
class AssemblyPipeline:
    def run(self,article,images,uploaded,output_dir):
        body=article['body']; meta={x['id']:x for x in images}; up={x['id']:x for x in uploaded}
        for iid in meta:
            m=up[iid]
            fig=f'<figure class="ficool-article-image"><img src="{html.escape(m["source_url"])}" alt="{html.escape(meta[iid]["alt"])}" width="{meta[iid]["width"]}" height="{meta[iid]["height"]}" loading="lazy"><figcaption>{html.escape(meta[iid]["caption"])}</figcaption></figure>'
            anchor=f'<!-- IMAGE: {iid} -->'
            if anchor in body: body=body.replace(anchor,fig,1)
            elif iid=='IMG-001': body=re.sub(r'(^# .+$)',r'\1\n\n'+fig,body,count=1,flags=re.M)
            else: body += '\n\n'+fig+'\n'
        body=re.sub(r'<!-- INTERNAL:\s*([^|]+)\|\s*([^>]+?)\s*-->',r'<a href="\2">\1</a>',body)
        html_body=markdown(body,extensions=['extra','tables']); dump_yaml(output_dir/'assembled.yaml',{'html_length':len(html_body),'image_count':len(images)}); (output_dir/'article.html').write_text(html_body,encoding='utf-8'); return html_body
