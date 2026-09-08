from .client import WordPressClient

def create_draft(client: WordPressClient, title: str, content: str, slug: str, categories=None, tags=None, featured_media=None, meta=None):
    payload = {"title": title, "content": content, "slug": slug, "status": "draft", "categories": categories or [], "tags": tags or []}
    if featured_media:
        payload["featured_media"] = featured_media
    if meta:
        payload["meta"] = meta
    return client.create_post(payload)
