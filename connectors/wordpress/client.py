from __future__ import annotations
import mimetypes, os
from pathlib import Path
from typing import Any
import requests


class WordPressError(RuntimeError):
    pass


class WordPressClient:
    def __init__(self, base_url=None, username=None, application_password=None, timeout=30):
        self.base_url = (base_url or os.getenv("WP_URL", "")).rstrip("/")
        self.username = username or os.getenv("WP_USERNAME", "")
        self.application_password = application_password or os.getenv("WP_APPLICATION_PASSWORD", "")
        self.timeout = timeout
        self.api = self.base_url + "/wp-json/wp/v2"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        if not all([self.base_url, self.username, self.application_password]):
            raise WordPressError("WordPress credentials are not configured")
        kwargs.setdefault("timeout", self.timeout)
        response = requests.request(method, self.api + path, auth=(self.username, self.application_password), **kwargs)
        if not response.ok:
            raise WordPressError(f"WP {method} {path} -> {response.status_code}: {response.text[:500]}")
        return response.json()

    # ── bài viết ────────────────────────────────────────────────────────────
    def create_post(self, payload: dict) -> dict:
        return self._request("POST", "/posts", json=payload)

    def get_post(self, post_id: int) -> dict:
        return self._request("GET", f"/posts/{post_id}")

    def find_posts_by_slug(self, slug: str) -> list:
        # status=any cần quyền đọc bản nháp; application password của biên tập viên có.
        return self._request("GET", "/posts", params={"slug": slug, "status": "any", "per_page": 100})

    # ── phân loại ───────────────────────────────────────────────────────────
    def find_term(self, taxonomy: str, name: str):
        """Trả về term khớp CHÍNH XÁC tên (không phân biệt hoa thường), hoặc None.

        `?search=` của WordPress khớp mờ: tìm 'Máy lạnh' có thể trả về cả
        'Máy lạnh công nghiệp'. Lấy bừa phần tử đầu là gán sai chuyên mục.
        """
        rows = self._request("GET", f"/{taxonomy}", params={"search": name, "per_page": 100})
        target = name.strip().casefold()
        for row in rows:
            if str(row.get("name", "")).strip().casefold() == target:
                return row
        return None

    def create_term(self, taxonomy: str, name: str) -> dict:
        return self._request("POST", f"/{taxonomy}", json={"name": name})

    # ── media ───────────────────────────────────────────────────────────────
    def upload_media(self, source, filename: str = None, mime_type: str = None, **meta) -> dict:
        """Nhận bytes hoặc đường dẫn file. `meta` nhận title/alt_text/caption/description.

        WordPress đặt metadata qua một lượt POST thứ hai lên /media/<id>; gửi kèm
        lượt tải nhị phân thì bị bỏ qua.
        """
        if isinstance(source, (str, Path)):
            path = Path(source)
            content = path.read_bytes()
            filename = filename or path.name
        else:
            content = source
            if not filename:
                raise WordPressError("upload_media: cần filename khi truyền bytes")
        mime_type = mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        created = self._request(
            "POST", "/media", data=content,
            headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime_type},
        )
        fields = {k: v for k, v in meta.items() if v}
        if fields:
            created = self._request("POST", f"/media/{created['id']}", json=fields)
        return created

    def delete_media(self, media_id: int) -> dict:
        # force=true: WordPress không cho media vào thùng rác, phải xoá thẳng.
        return self._request("DELETE", f"/media/{media_id}", params={"force": "true"})
