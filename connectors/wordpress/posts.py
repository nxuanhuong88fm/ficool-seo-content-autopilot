from __future__ import annotations
from .client import WordPressClient


def ids_for_taxonomy(client: WordPressClient, taxonomy: str, names) -> list:
    """Đổi tên chuyên mục/thẻ thành id, tạo mới nếu chưa có.

    taxonomy: 'categories' hoặc 'tags'.
    """
    ids = []
    for name in names or []:
        name = str(name).strip()
        if not name:
            continue
        term = client.find_term(taxonomy, name) or client.create_term(taxonomy, name)
        ids.append(term["id"])
    return ids


def create_draft(client: WordPressClient, title: str, content: str, slug: str,
                 excerpt: str = "", categories=None, tags=None,
                 featured_media=None, meta=None, author=None) -> dict:
    payload = {
        "title": title, "content": content, "slug": slug, "status": "draft",
        "categories": categories or [], "tags": tags or [],
    }
    if excerpt:
        payload["excerpt"] = excerpt
    if featured_media:
        payload["featured_media"] = featured_media
    if meta:
        payload["meta"] = meta
    if author:
        payload["author"] = int(author)
    return client.create_post(payload)
