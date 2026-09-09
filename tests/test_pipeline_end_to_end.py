"""Chạy pipeline/run.py từ đầu tới cuối, KHÔNG cần khoá thật.

Đây là phép đo mà CI cũ không có: validate_repo.py chỉ kiểm file có tồn tại,
còn test cũ chỉ chạy nhánh demo. Không gì chạm vào pipeline/.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.fake_wp import FakeWordPress  # noqa: E402

from pipeline.bai_mau import bai_mau  # noqa: E402

BAI = bai_mau("máy lạnh chảy nước trong nhà")

META = {"title": "Máy lạnh chảy nước trong nhà: cách xử lý",
        "meta_description": "Nguyên nhân máy lạnh chảy nước, cách kiểm tra an toàn và khi nào nên gọi kỹ thuật viên tại TP.HCM.",
        "slug": "may-lanh-chay-nuoc-trong-nha", "secondary_keywords": ["máy lạnh chảy nước"], "faq": []}


@pytest.fixture(autouse=True)
def so_sach(monkeypatch, tmp_path):
    """Sổ chống trùng phải cách ly, nếu không lượt test thứ hai tự chặn chính nó."""
    import pipeline.manifest
    monkeypatch.setattr(pipeline.manifest, "THU_MUC", tmp_path / "manifests")


@pytest.fixture
def wp_gia(monkeypatch):
    import requests
    fake = FakeWordPress()
    monkeypatch.setattr(requests, "request", fake.request)
    monkeypatch.setenv("WP_URL", "https://ficool.top")
    monkeypatch.setenv("WP_USERNAME", "bot")
    monkeypatch.setenv("WP_APPLICATION_PASSWORD", "x x x x")
    return fake


@pytest.fixture
def dich_vu_gia(monkeypatch, tmp_path):
    """Chặn ở ranh giới: OpenAI, GSC, Serper. Code của repo chạy thật."""
    import pipeline.article, pipeline.research, pipeline.images

    monkeypatch.setenv("OPENAI_API_KEY", "khoa-gia-cho-phep-thu")

    class _OpenAIGia:
        def __init__(self, *a, **k): self.responses = self
        def create(self, model=None, input="", store=False, **k):
            la_meta = input.lstrip().startswith("Return JSON only")
            return type("R", (), {"output_text": json.dumps(META, ensure_ascii=False) if la_meta else BAI})()

    monkeypatch.setattr(pipeline.article, "OpenAI", _OpenAIGia)

    class _NghienCuuGia:
        def run(self, topic, output_dir):
            return {"topic": topic, "serp": [{"title": "x", "link": "https://vd.vn/a"}],
                    "ai_research": {"sources": ["https://vd.vn/a"]}}
    monkeypatch.setattr(pipeline.research, "ResearchPipeline", _NghienCuuGia)
    monkeypatch.setattr("pipeline.run.ResearchPipeline", _NghienCuuGia)

    from connectors.image_provider import GeneratedImage

    class _AnhGia:
        def generate(self, prompt, output_path, width=1600, height=900):
            output_path = Path(output_path).with_suffix(".png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
            return GeneratedImage(output_path, 1536, 1024, "image/png", "gia")
    monkeypatch.setattr(pipeline.images, "OpenAIImageProvider", lambda *a, **k: _AnhGia())


def test_chay_het_pipeline_ra_ban_nhap(wp_gia, dich_vu_gia, tmp_path):
    from pipeline.run import run_topic
    root, qa, wp = run_topic("ML-01", output_root=tmp_path)

    assert qa["status"] == "PASS", f"QA chặn: {qa}"
    assert wp["status"] == "draft", f"khong phai ban nhap: {wp}"

    payload = next(b for m, p, _, b in wp_gia.calls if m == "POST" and p == "/posts")
    assert payload is not None
    html = payload["content"]

    # ① luôn là draft, không bao giờ publish
    assert payload["status"] == "draft"
    # ② liên kết nội bộ phải thành thẻ <a> thật
    assert '<a href="/bang-gia/">bảng giá dịch vụ</a>' in html
    # ③ danh sách phải có <ul> bọc — HTML hợp lệ
    assert "<ul>" in html and "<li>" in html
    # ④ bảng Markdown phải thành <table>
    assert "<table>" in html
    # ⑤ in đậm phải được xử lý
    assert "**gas**" not in html
    # ⑥ ảnh phải trỏ URL WordPress, không còn đường dẫn máy
    assert "wp-content/uploads" in html and str(tmp_path) not in html
    # ⑦ ảnh phải có alt và được gán featured
    assert payload["featured_media"] in wp_gia.media
    assert all(m.get("alt_text") for m in wp_gia.media.values()), "media thieu alt_text"
    # ⑧ chuyên mục/thẻ phải được gán
    assert payload["categories"] and payload["tags"]
    # ⑨ excerpt = meta description
    assert payload["excerpt"] == META["meta_description"]

    # ⑩ schema GEO phải nằm TRONG bài được đăng, và chỉ gồm type Rank Math bỏ trống
    import json as _j
    from pipeline.geo import TYPE_RANK_MATH_GIU
    khoi = re.search(r'application/ld\+json">(.*?)</script>', html, re.S)
    assert khoi, 'khong co JSON-LD trong bai duoc dang'
    do_thi = _j.loads(khoi.group(1))
    types = {n['@type'] for n in do_thi['@graph']}
    assert 'FAQPage' in types
    assert not (types & TYPE_RANK_MATH_GIU), f'lan sang type cua Rank Math: {types}'
