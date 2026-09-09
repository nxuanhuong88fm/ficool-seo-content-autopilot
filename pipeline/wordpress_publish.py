from __future__ import annotations
import os
from connectors.wordpress import WordPressClient, create_draft, ids_for_taxonomy, verify_post


class WordPressPipeline:
    def __init__(self, client=None):
        self.client = client or WordPressClient()

    def tai_anh(self, images):
        """Tải ảnh lên TRƯỚC khi dựng HTML, để QA soi đúng bài sẽ được đăng.

        Bản cũ dựng HTML bằng đường dẫn trên máy, cho QA duyệt, RỒI mới thay
        bằng URL WordPress — nên thứ được duyệt không phải thứ được đăng.
        """
        uploaded = []
        for item in images:
            wp = self.client.upload_media(
                item['local_path'], title=item['title'], alt_text=item['alt'],
                caption=item['caption'], description=item['caption'])
            uploaded.append({**item, 'media_id': wp['id'],
                             'source_url': wp.get('source_url') or wp.get('guid', {}).get('rendered', '')})
        return uploaded

    def don_anh(self, uploaded):
        """Gỡ ảnh đã tải khi bài bị QA chặn — không để lại file mồ côi."""
        for item in uploaded:
            try:
                self.client.delete_media(item['media_id'])
            except Exception:
                pass

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        slug = article['slug']
        trung = self.client.find_posts_by_slug(slug)
        if trung:
            raise RuntimeError(f'TRUNG SLUG: /{slug}/ da ton tai (post {[p["id"] for p in trung]})')

        categories = ids_for_taxonomy(self.client, 'categories', [topic['category']])
        tags = ids_for_taxonomy(self.client, 'tags', topic.get('tags', []))

        meta = {}
        tf, df = os.getenv('WP_META_TITLE_FIELD', ''), os.getenv('WP_META_DESCRIPTION_FIELD', '')
        if tf:
            meta[tf] = article['seo'].get('title')
        if df:
            meta[df] = article['seo'].get('meta_description')

        post = create_draft(
            self.client,
            title=article['seo'].get('title') or topic['title'],
            content=html_body, slug=slug,
            excerpt=article['seo'].get('meta_description', ''),
            categories=categories, tags=tags,
            featured_media=uploaded[0]['media_id'] if uploaded else None,
            meta=meta or None, author=os.getenv('WP_AUTHOR_ID') or None)

        verified = verify_post(self.client, post['id'], 'draft')
        if not verified['passed']:
            raise RuntimeError(f'XAC MINH HONG: {verified}')
        return {'post_id': post['id'], 'status': verified['status'],
                'link': verified['link'], 'media': uploaded}
