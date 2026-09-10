"""Ba đường công bố.

`ho-so` là mặc định vì cách làm đã chốt là CÓ NGƯỜI: Python làm phần xác định
được, tác nhân đăng qua MCP — bên đã có quyền mà không cần một biến WP_* nào.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from connectors.wordpress.ability import NovamiraClient, NovamiraError
from connectors.wordpress.publishers import (MOC_ANH, CongBoHoSo, CongBoNovamira,
                                             CongBoRest, chon_cong_bo)

TOPIC = {'id': 'ML-01', 'title': 'May lanh chay nuoc', 'category': 'May lanh',
         'tags': ['loi thuong gap'], 'primary_keyword': 'may lanh chay nuoc'}
ART = {'slug': 'may-lanh-chay-nuoc',
       'seo': {'title': 'May lanh chay nuoc: xu ly', 'meta_description': 'Mo ta ngan.'}}
KHOA = ('WP_URL', 'WP_USERNAME', 'WP_APPLICATION_PASSWORD')


def _anh(tmp_path, n=2):
    ra = []
    for i in range(1, n + 1):
        p = tmp_path / 'images' / ('img-%03d.png' % i)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'\x89PNG\r\n\x1a\n' + bytes(64))
        ra.append({'id': 'IMG-%03d' % i, 'local_path': str(p), 'filename': p.name,
                   'alt': 'alt %d' % i, 'title': 'title %d' % i, 'caption': 'caption %d' % i,
                   'width': 1536, 'height': 1024})
    return ra


# ── chọn đường ──────────────────────────────────────────────────────────────
def test_mac_dinh_khong_can_khoa(tmp_path):
    cb = chon_cong_bo('ho-so', tmp_path)
    assert cb.ten == 'ho-so'
    assert cb.can_khoa is False
    assert cb.san_sang() is True


def test_auto_khong_co_khoa_thi_roi_ve_ho_so(monkeypatch, tmp_path):
    for k in KHOA:
        monkeypatch.delenv(k, raising=False)
    assert chon_cong_bo('auto', tmp_path).ten == 'ho-so'


def test_che_do_la_thi_bao_loi(tmp_path):
    with pytest.raises(ValueError, match='khong hop le'):
        chon_cong_bo('linh-tinh', tmp_path)


def test_duong_rest_thieu_khoa_thi_chua_san_sang(monkeypatch):
    for k in KHOA:
        monkeypatch.delenv(k, raising=False)
    assert CongBoRest.can_khoa is True
    assert CongBoRest().san_sang() is False


# ── đường hồ sơ ─────────────────────────────────────────────────────────────
def test_ho_so_ghi_du_goi_ban_giao(tmp_path):
    cb = CongBoHoSo(tmp_path)
    up = cb.tai_anh(_anh(tmp_path))

    assert all(u['source_url'] == MOC_ANH.format(id=u['id']) for u in up)
    assert all(u['media_id'] is None for u in up)

    html = '<h1>x</h1><img src="' + up[0]['source_url'] + '">'
    kq = cb.dang_ban_nhap(TOPIC, ART, html, up)
    goi = Path(kq['goi'])

    assert kq['status'] == 'cho_tac_nhan'
    assert kq['post_id'] is None
    assert (goi / 'noi-dung.html').read_text(encoding='utf-8') == html
    assert sorted(p.name for p in (goi / 'images').iterdir()) == ['img-001.png', 'img-002.png']

    kh = json.loads((goi / 'ke-hoach.json').read_text(encoding='utf-8'))
    assert kh['slug'] == ART['slug']
    assert [b['thu_tu'] for b in kh['buoc']] == [0, 1, 2, 3, 4, 5, 6]
    assert kh['buoc'][3]['tham_so']['post_status'] == 'draft'
    assert kh['buoc'][4]['tham_so']['focus_keywords'] == [TOPIC['primary_keyword']]
    assert len(kh['anh']) == 2
    assert kh['anh'][0]['alt'] == 'alt 1'


def test_ho_so_moi_moc_trong_html_deu_co_trong_ke_hoach(tmp_path):
    """Thiếu một mục là tác nhân để lại @@ANH: nguyên trong bài đã đăng."""
    cb = CongBoHoSo(tmp_path)
    up = cb.tai_anh(_anh(tmp_path, 4))
    html = ''.join('<img src="' + u['source_url'] + '">' for u in up)
    kq = cb.dang_ban_nhap(TOPIC, ART, html, up)
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))
    for a in kh['anh']:
        assert a['moc_thay_the'] in html


def test_ho_so_bi_QA_chan_thi_xoa_goi(tmp_path):
    cb = CongBoHoSo(tmp_path)
    up = cb.tai_anh(_anh(tmp_path))
    cb.dang_ban_nhap(TOPIC, ART, '<h1>x</h1>', up)
    assert (tmp_path / 'goi-dang').exists()
    cb.don_anh(up)
    assert not (tmp_path / 'goi-dang').exists()


# ── đường novamira ──────────────────────────────────────────────────────────
class _NovaGia:
    def __init__(self, hong=False):
        self.hong = hong
        self.da_goi = []

    def san_sang(self):
        return True

    def chay(self, ten, dau_vao):
        self.da_goi.append((ten, dau_vao))
        if self.hong:
            raise NovamiraError('HTTP 403')
        return {'ok': True}


class _NovaCongBo(CongBoNovamira):
    """Thay phần REST bằng kết quả cố định, để chỉ đo phần Rank Math."""

    def __init__(self, nova):
        self.nova = nova

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        return CongBoNovamira.dang_ban_nhap(self, topic, article, html_body, uploaded)

    def _rest(self, *a, **k):
        return {'duong': 'rest', 'post_id': 42, 'status': 'draft',
                'link': 'https://ficool.top/?p=42', 'media': []}


def _cong_bo(nova, monkeypatch):
    cb = _NovaCongBo(nova)
    monkeypatch.setattr(CongBoRest, 'dang_ban_nhap',
                        lambda self, *a, **k: {'duong': 'rest', 'post_id': 42, 'status': 'draft',
                                               'link': 'https://ficool.top/?p=42', 'media': []})
    return cb


def test_novamira_ghi_meta_rank_math(monkeypatch):
    n = _NovaGia()
    kq = _cong_bo(n, monkeypatch).dang_ban_nhap(TOPIC, ART, '<h1>x</h1>', [])

    assert kq['rank_math'] == 'da ghi'
    ten, dau_vao = n.da_goi[0]
    assert ten == 'novamira/rank-math-edit-post-seo'
    assert dau_vao['post_id'] == 42
    assert dau_vao['seo_title'] == ART['seo']['title']
    assert dau_vao['meta_description'] == ART['seo']['meta_description']
    assert dau_vao['focus_keywords'] == [TOPIC['primary_keyword']]


def test_rank_math_hong_thi_khong_lam_hong_ca_luot(monkeypatch):
    """Bài đã tạo xong. Ném lỗi ở đây là bỏ lại một bản nháp mồ côi."""
    kq = _cong_bo(_NovaGia(hong=True), monkeypatch).dang_ban_nhap(TOPIC, ART, '<h1>x</h1>', [])
    assert kq['post_id'] == 42
    assert kq['status'] == 'draft'
    assert kq['rank_math'].startswith('HONG:')


# ── client ability ──────────────────────────────────────────────────────────
def test_ability_thieu_khoa_thi_bao_ro(monkeypatch):
    for k in KHOA:
        monkeypatch.delenv(k, raising=False)
    c = NovamiraClient()
    assert c.du_khoa() is False
    assert c.san_sang() is False
    with pytest.raises(NovamiraError, match='thieu WP_URL'):
        c.chay('novamira/agent-context', {})


def test_ability_goi_dung_tuyen_va_boc_du_lieu(monkeypatch):
    goi = {}

    class _R:
        ok = True
        status_code = 200
        text = ''

        @staticmethod
        def json():
            return {'success': True, 'data': {'ket_qua': 'ok'}}

    def _post(url, json=None, auth=None, timeout=None):
        goi.update(url=url, json=json, auth=auth)
        return _R()

    monkeypatch.setattr('connectors.wordpress.ability.requests.post', _post)
    c = NovamiraClient(base_url='https://ficool.top', username='u', application_password='p')

    assert c.chay('novamira/create-post', {'a': 1}) == {'ket_qua': 'ok'}
    assert goi['url'] == 'https://ficool.top/wp-json/novamira/v1/abilities/novamira/create-post/run'
    assert goi['json'] == {'input': {'a': 1}}
    assert goi['auth'] == ('u', 'p')


def test_ability_loi_HTTP_thi_goi_lai_thanh_NovamiraError(monkeypatch):
    class _R:
        ok = False
        status_code = 403
        text = 'novamira_forbidden'

        @staticmethod
        def json():
            return {}

    monkeypatch.setattr('connectors.wordpress.ability.requests.post',
                        lambda *a, **k: _R())
    c = NovamiraClient(base_url='https://ficool.top', username='u', application_password='p')
    with pytest.raises(NovamiraError, match='403'):
        c.chay('novamira/create-post', {})


def test_ke_hoach_co_danh_sach_kiem_sau_dang(tmp_path):
    """Đường ho-so buộc phải QA TRƯỚC lúc thay URL ảnh — tác nhân chỉ biết
    media_id sau khi tải lên. Phần QA không phủ được phải thành danh sách kiểm
    rõ ràng, nếu không bước thay chuỗi nằm ngoài mọi cổng."""
    cb = CongBoHoSo(tmp_path)
    up = cb.tai_anh(_anh(tmp_path, 3))
    kq = cb.dang_ban_nhap(TOPIC, ART, '<h1>x</h1>', up)
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))

    ds = kh['kiem_sau_dang']
    assert any('draft' in x for x in ds)
    assert any('@@ANH:' in x for x in ds)
    assert any('wp-content/uploads' in x for x in ds)
    assert any('bang 3' in x for x in ds)          # đúng số ảnh
    assert any(ART['slug'] in x for x in ds)
    assert any('FAQPage' in x for x in ds)


def test_demo_sinh_goi_tu_nhat_quan(tmp_path, monkeypatch):
    """Chạy demo thật: cách DUY NHẤT đo được đường ho-so đầu-tới-cuối mà không
    tốn một dòng khoá API nào."""
    import pipeline.cli as cli
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    ma = cli.main(['demo', 'may lanh chay nuoc trong nha'])
    assert ma == 0

    goi = tmp_path / 'output/demo/may-lanh-chay-nuoc-trong-nha/goi-dang'
    kh = json.loads((goi / 'ke-hoach.json').read_text(encoding='utf-8'))
    html = (goi / 'noi-dung.html').read_text(encoding='utf-8')

    assert len(kh['anh']) == 4
    # Anh `featured` di vao O ANH DAI DIEN (template #268 render), khong vao
    # post_content — no co TEP nhung khong co moc trong HTML.
    assert [a['o'] for a in kh['anh']].count('anh dai dien (khong o trong bai)') == 1
    for a in kh['anh']:
        assert (goi / a['tep']).exists()
        if a['vai_tro'] != 'featured':
            assert a['moc_thay_the'] in html, 'moc %s khong co trong HTML' % a['id']
    assert kh['buoc'][3]['tham_so']['post_status'] == 'draft'
