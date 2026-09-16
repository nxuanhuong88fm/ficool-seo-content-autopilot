"""Chạy theo LÔ, thứ tự cố định.

Vì sao không dùng GSC lúc này: site đang `blog_public = 0`, chưa từng được lập
chỉ mục, nên mọi chủ đề cùng một điểm nền — đo được ở test cuối file. Xếp hạng
theo GSC khi không có dữ liệu GSC là chọn ngẫu nhiên nhưng trông như có căn cứ.
"""
from __future__ import annotations
import json

import pytest

import pipeline.cli as cli
import pipeline.manifest as manifest
from pipeline.chon import HetChuDe, chon_lo
from pipeline.prioritize import prioritize_topics
from pipeline.topic_selector import TopicSelector


@pytest.fixture(autouse=True)
def so_sach(monkeypatch, tmp_path):
    monkeypatch.setattr(manifest, 'THU_MUC', tmp_path / 'manifests')
    return tmp_path / 'manifests'


# ── chọn lô ─────────────────────────────────────────────────────────────────
def test_mac_dinh_la_P1_truoc_theo_nguyen_tac_1_cua_khach():
    """Sheet "Cách triển khai", nguyên tắc 1: "Không publish theo thứ tự STT —
    Ưu tiên P1 trước". Mặc định cũ ('cum') đi thẳng ngược điều đó."""
    lo, con = chon_lo(10)
    assert all(t['priority'] == 'P1' for t in lo), [t['id'] for t in lo]
    assert con == 108

    # KHONG chi la thu tu STT doi ten: ML-07 va ML-08 la P2 nen phai bi day lui.
    ids = [t['id'] for t in lo]
    assert 'ML-07' not in ids and 'ML-08' not in ids
    assert 'ML-09' in ids


def test_thu_tu_cum_di_het_mot_dong_thiet_bi_truoc():
    lo, con = chon_lo(10, 'cum')
    assert [t['id'] for t in lo] == ['ML-%02d' % i for i in range(1, 11)]
    assert con == 108


def test_thu_tu_luan_phien_vong_qua_sau_dong():
    lo, _ = chon_lo(6, 'luan-phien')
    assert [t['id'] for t in lo] == ['ML-01', 'MG-01', 'TL-01', 'TD-01', 'MN-01', 'TK-01']


def test_bo_qua_chu_de_da_lam(so_sach):
    so_sach.mkdir(parents=True, exist_ok=True)
    for tid in ('ML-01', 'ML-02', 'ML-03'):
        (so_sach / (tid + '.json')).write_text(
            json.dumps({'run_id': tid, 'topic_id': tid}), encoding='utf-8')
    lo, con = chon_lo(3, 'cum')
    assert [t['id'] for t in lo] == ['ML-04', 'ML-05', 'ML-06']
    assert con == 105


def test_het_chu_de_thi_bao_ro(so_sach):
    so_sach.mkdir(parents=True, exist_ok=True)
    for t in TopicSelector().all():
        (so_sach / (t['id'] + '.json')).write_text(
            json.dumps({'run_id': t['id'], 'topic_id': t['id']}), encoding='utf-8')
    with pytest.raises(HetChuDe):
        chon_lo(1)


@pytest.mark.parametrize('xau', [0, -1])
def test_so_luong_vo_ly_thi_chan(xau):
    with pytest.raises(ValueError, match='so_luong'):
        chon_lo(xau)


def test_thu_tu_la_thi_chan():
    with pytest.raises(ValueError, match='thu_tu'):
        chon_lo(3, 'linh-tinh')


# ── chạy lô ─────────────────────────────────────────────────────────────────
def _gia_run(ket_qua):
    """ket_qua: dict topic_id -> 'ok' | Exception."""
    def _f(topic_id, **k):
        r = ket_qua.get(topic_id, 'ok')
        if isinstance(r, Exception):
            raise r
        return ('/tmp/' + topic_id, {'overall': 100, 'status': 'PASS'},
                {'duong': 'ho-so', 'status': 'cho_tac_nhan', 'goi': '/tmp/%s/goi-dang' % topic_id})
    return _f


def test_mot_bai_hong_khong_giet_ca_lo(monkeypatch, capsys):
    """Chín bài kia đã tốn tiền API rồi — dừng cả lô là vứt luôn số tiền đó."""
    import pipeline.run as pr
    monkeypatch.setattr(pr, 'run_topic', _gia_run({'ML-03': RuntimeError('mang chap chon')}))

    ma = cli.main(['lo', '5', '--mock-images'])
    ra = capsys.readouterr().out

    assert ma == 1                       # co bai hong -> ma thoat khac 0
    assert 'HONG: RuntimeError: mang chap chon' in ra
    assert 'Xong 4/5 bai.' in ra
    assert 'ML-05' in ra                 # van chay tiep sau bai hong


def test_QA_chan_duoc_ghi_rieng(monkeypatch, capsys):
    import pipeline.run as pr
    monkeypatch.setattr(pr, 'run_topic', _gia_run({'ML-02': pr.QAChan('thieu FAQ')}))
    cli.main(['lo', '3', '--mock-images'])
    ra = capsys.readouterr().out
    assert 'QA CHAN: thieu FAQ' in ra
    assert 'Xong 2/3 bai.' in ra


def test_xem_truoc_khong_chay_gi(monkeypatch, capsys):
    import pipeline.run as pr

    def _no(*a, **k):
        raise AssertionError('xem-truoc ma van goi run_topic')

    monkeypatch.setattr(pr, 'run_topic', _no)
    assert cli.main(['lo', '4', '--xem-truoc']) == 0
    ra = capsys.readouterr().out
    assert 'chua chay' in ra
    assert '4 anh' not in ra or 'Uoc luong' in ra


def test_lo_bao_uoc_luong_goi_api(monkeypatch, capsys):
    """Uoc luong phai noi dung so tien SE tieu.

    Mac dinh la `--anh=giu-cho`: khong goi lan nao. Van bao "40 anh" o day la
    noi sai ve tien — dung thu khach doc de quyet dinh co chay hay khong, va
    day chinh la ly do doi mac dinh (10/09/2026).
    """
    cli.main(['lo', '10', '--xem-truoc'])
    ra = capsys.readouterr().out
    assert '10 luot nghien cuu' in ra
    assert '40 anh' not in ra
    assert 'KHONG sinh' in ra


def test_lo_bao_TIEN_khi_khai_ro_anh_gemini(capsys):
    cli.main(['lo', '10', '--xem-truoc', '--anh=gemini'])
    ra = capsys.readouterr().out
    assert '40 anh' in ra and '$2.68' in ra


# ── sổ: gói đang chờ và đóng sổ ─────────────────────────────────────────────
def test_dang_cho_va_dong_so(so_sach, capsys):
    so_sach.mkdir(parents=True, exist_ok=True)
    (so_sach / 'ML-01-abc.json').write_text(json.dumps({
        'run_id': 'ML-01-abc', 'topic_id': 'ML-01', 'topic': 'May lanh chay nuoc',
        'slug': 'may-lanh-chay-nuoc', 'wp_status': 'cho_tac_nhan', 'wp_post_id': None,
    }, ensure_ascii=False), encoding='utf-8')

    assert len(manifest.dang_cho()) == 1
    assert cli.main(['cho-dang']) == 0
    assert 'ML-01-abc' in capsys.readouterr().out

    manifest.danh_dau_da_dang('ML-01-abc', 4242, 'https://ficool.top/?p=4242')
    assert manifest.dang_cho() == []

    d = json.loads((so_sach / 'ML-01-abc.json').read_text(encoding='utf-8'))
    assert d['wp_post_id'] == 4242 and d['wp_status'] == 'draft'
    assert d['wp_link'].endswith('4242') and 'dang_luc' in d


def test_dong_so_luot_khong_ton_tai_thi_bao_loi(so_sach):
    with pytest.raises(FileNotFoundError, match='khong thay so'):
        manifest.danh_dau_da_dang('khong-co', 1)


# ── vì sao bỏ GSC lúc này ───────────────────────────────────────────────────
def test_khong_co_du_lieu_GSC_thi_moi_chu_de_cung_diem_nen():
    """Bằng chứng cho quyết định dùng thứ tự cố định thay vì xếp hạng."""
    xep = prioritize_topics(TopicSelector().all(), [])
    diem = {t['gsc_priority_score'] for t in xep}
    assert len(diem) <= 2, 'khong con la diem nen dong deu: %s' % diem
