import os
from typing import Any
import requests

class WordPressClient:
    def __init__(self, base_url=None, username=None, application_password=None):
        self.base_url = (base_url or os.getenv("WP_URL", "")).rstrip("/")
        self.username = username or os.getenv("WP_USERNAME", "")
        self.application_password = application_password or os.getenv("WP_APPLICATION_PASSWORD", "")
        self.api = self.base_url + "/wp-json/wp/v2"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        if not all([self.base_url, self.username, self.application_password]):
            raise RuntimeError("WordPress credentials are not configured")
        return requests.request(method, self.api + path, auth=(self.username, self.application_password), timeout=30, **kwargs)

    def create_post(self, payload: dict) -> dict:
        response = self._request("POST", "/posts", json=payload)
        response.raise_for_status()
        return response.json()

    def upload_media(self, content: bytes, filename: str, mime_type: str = "image/webp") -> dict:
        response = self._request("POST", "/media", data=content, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime_type})
        response.raise_for_status()
        return response.json()

    def get_post(self, post_id: int) -> dict:
        response = self._request("GET", f"/posts/{post_id}")
        response.raise_for_status()
        return response.json()
