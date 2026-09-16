"""Gọi ability của plugin novamira qua HTTP.

Đo trên ficool.top 09/09/2026:

    POST /wp-json/novamira/v1/abilities/{ten}/run   -> 401 khi chưa đăng nhập
    permission_callback = novamira_rest_run_ability_permission
        (rest-shim.php:45 — chỉ kiểm novamira_is_enabled + current_user_can_manage)

Nghĩa là ability dùng ĐÚNG bộ xác thực như REST lõi: application password.
Không phải một kênh riêng, cũng không cần MCP.

Vì sao đáng dùng thay REST lõi ở vài chỗ: Rank Math. Ghi meta title/description
qua REST lõi phải ĐOÁN tên trường qua biến `WP_META_TITLE_FIELD` — đoán sai thì
meta im lặng không được ghi. `novamira/rank-math-edit-post-seo` coi đó là thao
tác hạng nhất.
"""
from __future__ import annotations
import os
import requests

TUYEN = '/wp-json/novamira/v1/abilities/{ten}/run'


class NovamiraError(RuntimeError):
    pass


class NovamiraClient:
    def __init__(self, base_url=None, username=None, application_password=None, timeout=30):
        self.base_url = (base_url or os.getenv('WP_URL', '')).rstrip('/')
        self.username = username or os.getenv('WP_USERNAME', '')
        self.mat_khau = application_password or os.getenv('WP_APPLICATION_PASSWORD', '')
        self.timeout = timeout

    def du_khoa(self) -> bool:
        return all([self.base_url, self.username, self.mat_khau])

    def san_sang(self) -> bool:
        """Plugin có mặt VÀ khoá dùng được? Đo bằng một lượt gọi thật.

        Không đoán theo tên miền: plugin tắt được, và khoá hết hạn được.
        """
        if not self.du_khoa():
            return False
        try:
            self.chay('novamira/agent-context', {})
            return True
        except NovamiraError:
            return False

    def chay(self, ten: str, dau_vao: dict):
        if not self.du_khoa():
            raise NovamiraError('thieu WP_URL / WP_USERNAME / WP_APPLICATION_PASSWORD')
        r = requests.post(
            self.base_url + TUYEN.format(ten=ten),
            json={'input': dau_vao},
            auth=(self.username, self.mat_khau),
            timeout=self.timeout,
        )
        if not r.ok:
            raise NovamiraError(f'{ten} -> HTTP {r.status_code}: {r.text[:400]}')
        d = r.json()
        if isinstance(d, dict) and d.get('success') is False:
            raise NovamiraError(f'{ten} -> {d}')
        return d.get('data', d) if isinstance(d, dict) else d
