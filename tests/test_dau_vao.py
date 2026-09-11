"""Đầu vào do tác nhân cung cấp — hai cần gạt `--nghien-cuu=toi` và `--viet=toi`.

Test cuối là quan trọng nhất: chạy TOÀN TUYẾN tới gói bàn giao mà KHÔNG một khoá
API nào được đặt. Đó là phương án (a) ở dạng thuần nhất.
"""
from __future__ import annotations
import re

import pytest
import yaml

import pipeline.manifest as manifest
from pipeline.bai_mau import bai_mau
from pipeline.dau_vao import (DauVaoSai, ThieuDauVao, doc_bai_viet, doc_nghien_cuu,
                              duong_dan, ghi_mau)
from pipeline.topic_selector import TopicSelector

TOPIC = TopicSelector().by_id('ML-01')

NGUON = [{'url': 'https://vnexpress.net/a', 'title': 'A'},
         {'url': 'https://tuoitre.vn/b', 'title': 'B'}]
VAN_BAN = 'Nuoc ngung tu chay ra tu mang hung khi mang bi nghen. ' * 8


def _ghi(tmp_path, nghien_cuu=None, bai_viet=None, topic_id='ML-01'):
    p = duong_dan(topic_id, tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    d = {}
    if nghien_cuu is not None:
        d['nghien_cuu'] = nghien_cuu
    if bai_viet is not None:
        d['bai_viet'] = bai_viet
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return p


def _nghien_cuu_dat():
    return {'van_ban': VAN_BAN, 'nguon': list(NGUON), 'serp': []}


def _bai_viet_dat():
    than = bai_mau('máy lạnh chảy nước trong nhà')
    return {'than': than,
            'seo': {'tieu_de': 'Máy lạnh chảy nước trong nhà: cách xử lý',
                    'mo_ta': 'Nguyên nhân máy lạnh chảy nước, cách kiểm tra an toàn '
                             'và khi nào nên gọi kỹ thuật viên tại TP.HCM.',
                    'slug': 'may-lanh-chay-nuoc-trong-nha', 'tu_khoa_phu': []}}


# ── thiếu tệp ───────────────────────────────────────────────────────────────
def test_thieu_tep_thi_chi_ro_duong_dan_va_cach_sinh(tmp_path):
    with pytest.raises(ThieuDauVao, match='ficool yeu-cau'):
        doc_nghien_cuu(TOPIC, tmp_path)


# ── nghiên cứu: mỗi luật phải chặn được ─────────────────────────────────────
def test_nghien_cuu_dat(tmp_path):
    _ghi(tmp_path, nghien_cuu=_nghien_cuu_dat())
    r = doc_nghien_cuu(TOPIC, tmp_path)
    assert len(r['ai_research']['sources']) == 2
    assert r['nguon_goc'] == 'tac_nhan'


@pytest.mark.parametrize('be,mong', [
    (lambda d: d.update(van_ban='ngan qua'), 'van_ban chi'),
    (lambda d: d.update(nguon=[]), 'nguon co 0'),
    (lambda d: d.update(nguon=[{'url': 'khong-phai-url', 'title': 'x'}]), 'nguon co 0'),
    (lambda d: d.update(nguon=[NGUON[0]]), 'nguon co 1'),
])
def test_nghien_cuu_thieu_thi_chan(tmp_path, be, mong):
    """Nộp thiếu nguồn mà lọt là cổng QA `co_nguon` mất căn cứ — đúng lỗi của
    openai_research.py cũ, luôn trả sources: [] mà không ai biết."""
    d = _nghien_cuu_dat()
    be(d)
    _ghi(tmp_path, nghien_cuu=d)
    with pytest.raises(DauVaoSai, match=mong):
        doc_nghien_cuu(TOPIC, tmp_path)


# ── bài viết: mỗi luật phải chặn được ───────────────────────────────────────
def test_bai_viet_dat(tmp_path):
    _ghi(tmp_path, bai_viet=_bai_viet_dat())
    a = doc_bai_viet(TOPIC, tmp_path)
    assert a['slug'] == 'may-lanh-chay-nuoc-trong-nha'
    assert a['seo']['title'] == a['title']
    assert re.search(r'^# ', a['body'], re.M)


@pytest.mark.parametrize('be,mong', [
    (lambda d: d.update(than='Qua ngan.'), 'than co'),
    (lambda d: d.update(than='Khong co tieu de. ' * 500), 'thieu dong'),
    (lambda d: d['seo'].update(tieu_de='x' * 61), 'tieu_de dai 61'),
    (lambda d: d['seo'].update(tieu_de=''), 'tieu_de dai 0'),
    (lambda d: d['seo'].update(mo_ta='y' * 161), 'mo_ta dai 161'),
    (lambda d: d['seo'].update(slug='Slug Co Dau Cach'), 'khong phai slug'),
    (lambda d: d['seo'].update(slug=''), 'khong phai slug'),
])
def test_bai_viet_sai_thi_chan(tmp_path, be, mong):
    d = _bai_viet_dat()
    be(d)
    _ghi(tmp_path, bai_viet=d)
    with pytest.raises(DauVaoSai, match=mong):
        doc_bai_viet(TOPIC, tmp_path)


# ── mẫu ─────────────────────────────────────────────────────────────────────
def test_mau_mang_nguyen_van_luat_viet(tmp_path):
    """Luật viết phải từ MỘT nguồn: dù tác nhân viết hay Gemini viết."""
    from pipeline.article import LUAT_VIET
    p = ghi_mau(TOPIC, tmp_path)
    d = yaml.safe_load(p.read_text(encoding='utf-8'))
    assert d['_luat_viet'] == LUAT_VIET
    assert d['chu_de']['id'] == 'ML-01'


def test_mau_khong_ghi_de_tep_da_dien(tmp_path):
    """Sinh lại mẫu mà xoá mất bài đã viết là mất công thật."""
    _ghi(tmp_path, nghien_cuu=_nghien_cuu_dat())
    truoc = duong_dan('ML-01', tmp_path).read_text(encoding='utf-8')
    ghi_mau(TOPIC, tmp_path)
    assert duong_dan('ML-01', tmp_path).read_text(encoding='utf-8') == truoc


# ── toàn tuyến, KHÔNG một khoá API nào ──────────────────────────────────────
def test_toan_tuyen_khong_can_khoa_api(tmp_path, monkeypatch):
    """Phương án (a) thuần nhất: tác nhân nghiên cứu, tác nhân viết, ảnh giả.

    Không đặt GEMINI_API_KEY, WP_URL, SERPER_API_KEY hay GSC nao. Neu pipeline
    con dung mot connector thua thi test nay do.
    """
    for k in ('GEMINI_API_KEY', 'SERPER_API_KEY', 'GSC_SITE_URL',
              'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_APPLICATION_CREDENTIALS_JSON',
              'WP_URL', 'WP_USERNAME', 'WP_APPLICATION_PASSWORD'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(manifest, 'THU_MUC', tmp_path / 'manifests')

    dv = tmp_path / 'dau-vao'
    _ghi(dv, nghien_cuu=_nghien_cuu_dat(), bai_viet=_bai_viet_dat())

    from pipeline.run import run_topic
    root, qa, wp = run_topic('ML-01', output_root=tmp_path / 'runs',
                             use_mock_images=True, dang_bai='ho-so',
                             nghien_cuu='toi', viet='toi', thu_muc_dau_vao=dv)

    assert qa['status'] == 'PASS', qa['blockers']
    assert qa['checks']['co_nguon'] is True          # nguon that tu tac nhan
    assert wp['duong'] == 'ho-so' and wp['status'] == 'cho_tac_nhan'

    goi = tmp_path / 'runs' / root.name / 'goi-dang'
    assert (goi / 'ke-hoach.json').exists()
    assert (goi / 'noi-dung.html').exists()
    assert len(list((goi / 'images').iterdir())) == 4
    assert len(manifest.dang_cho()) == 1
