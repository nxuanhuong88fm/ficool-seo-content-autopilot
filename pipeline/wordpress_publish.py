from __future__ import annotations
import os
from connectors.wordpress import WordPressClient
from connectors.wordpress.posts import create_draft,ids_for_taxonomy
from connectors.wordpress.verify import verify_post
class WordPressPipeline:
    def __init__(self): self.client=WordPressClient()
    def run(self,topic,article,html_body,images):
        categories=ids_for_taxonomy(self.client,'categories',[topic['category']]); tags=ids_for_taxonomy(self.client,'tags',topic.get('tags',[]))
        uploaded=[]
        for item in images:
            wp=self.client.upload_media(item['local_path'],title=item['title'],alt_text=item['alt'],caption=item['caption'],description=item['caption'])
            uploaded.append({**item,'media_id':wp['id'],'source_url':wp.get('source_url',wp.get('guid',{}).get('rendered',''))})
        final=html_body
        for m in uploaded: final=final.replace(m['local_path'],m['source_url'])
        meta={}; tf=os.getenv('WP_META_TITLE_FIELD',''); df=os.getenv('WP_META_DESCRIPTION_FIELD','')
        if tf: meta[tf]=article['seo'].get('title')
        if df: meta[df]=article['seo'].get('meta_description')
        post=create_draft(self.client,title=article['seo'].get('title') or topic['title'],content=final,slug=article['slug'],excerpt=article['seo'].get('meta_description',''),categories=categories,tags=tags,featured_media=uploaded[0]['media_id'],meta=meta or None,author=os.getenv('WP_AUTHOR_ID') or None)
        verified=verify_post(self.client,post['id'],'draft'); return {'post_id':post['id'],'status':verified.get('status'),'link':verified.get('link'),'media':uploaded}
