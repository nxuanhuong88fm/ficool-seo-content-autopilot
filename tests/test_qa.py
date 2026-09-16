from __future__ import annotations
from pathlib import Path
import re
import pytest
import yaml

from pipeline.qa import QAPipeline, do_phu_tu_khoa, khang_dinh_bi_cam

ROOT = Path(__file__).resolve().parents[1]
LUAT = yaml.safe_load((ROOT / 'config/forbidden-claims.yaml').read_text(encoding='utf-8'))['luat']


def _vi_du(luat, khoa):
    """`chan`/`khong_chan` nhận CHUỖI hoặc DANH SÁCH chuỗi.

    Luật càng hẹp thì càng cần nhiều ví dụ mới khoá được hình dạng của nó. Ép
    mỗi luật chỉ một ví dụ là ép người viết luật chọn một ca rồi bỏ phần còn lại
    không ai đo — `so_sanh_nhat` có 9 ca `khong_chan`, mỗi ca là một lượt bắt
    nhầm THẬT đã xảy ra trên 108 bài.
    """
    v = luat[khoa]
    return [v] if isinstance(v, str) else list(v)


@pytest.mark.parametrize('luat', LUAT, ids=[l['ten'] for l in LUAT])
def test_moi_luat_cam_bat_dung_vi_du_chan(luat):
    for cau in _vi_du(luat, 'chan'):
        ten = [t for t, _ in khang_dinh_bi_cam(cau)]
        assert luat['ten'] in ten, \
            f"luat {luat['ten']} khong bat duoc vi du chan cua chinh no: {cau!r}"


@pytest.mark.parametrize('luat', LUAT, ids=[l['ten'] for l in LUAT])
def test_moi_luat_cam_tha_dung_vi_du_khong_chan(luat):
    """Chiều phủ định. Thiếu chiều này chính là cách lỗi `cam kết` lọt vào."""
    for cau in _vi_du(luat, 'khong_chan'):
        assert khang_dinh_bi_cam(cau) == [], \
            f"vi du hop le cua {luat['ten']} bi chan nham: {cau!r}"


@pytest.mark.parametrize('luat', LUAT, ids=[l['ten'] for l in LUAT])
def test_moi_luat_deu_co_du_hai_chieu(luat):
    """Luật thiếu một chiều thì nó lặng lẽ chặn nhầm — đúng lời mở đầu của
    chính `config/forbidden-claims.yaml`."""
    assert _vi_du(luat, 'chan'), luat['ten']
    assert _vi_du(luat, 'khong_chan'), luat['ten']


def test_cau_that_tren_trang_chu_ficool_khong_bi_chan():
    that = 'Những gì Ficool cam kết làm: kiểm tra trước, báo giá rõ, làm xong mới thu tiền.'
    assert khang_dinh_bi_cam(that) == []


def test_do_phu_tu_khoa():
    tk = 'khi nào máy lạnh cần bảo trì thay vì chỉ vệ sinh'
    du = 'Máy lạnh dùng lâu cần bảo trì chứ không phải chỉ vệ sinh định kỳ.'
    thieu = 'Tủ lạnh nhà bạn có thể kêu to vì nhiều lý do.'
    assert do_phu_tu_khoa(tk, du) >= 0.7
    assert do_phu_tu_khoa(tk, thieu) < 0.7


# ── cổng đầy đủ: một bộ dữ liệu ĐẠT, rồi bẻ từng phép một ──────────────────
def _bo_dat():
    than = ('# Máy lạnh chảy nước trong nhà\n\n' + 'Máy lạnh chảy nước trong nhà thường do máng nghẹt. '
            'Ficool phục vụ TP.HCM. Câu hỏi thường gặp bên dưới. ' * 60)
    return dict(
        topic={'primary_keyword': 'máy lạnh chảy nước trong nhà'},
        article={'body': than, 'seo': {'title': 'Máy lạnh chảy nước trong nhà: xử lý',
                                       'meta_description': 'Nguyên nhân và cách xử lý máy lạnh chảy nước tại TP.HCM.'}},
        html_body='<figure class="ficool-article-image"></figure>' * 4 + '<a href="/bang-gia/">giá</a>',
        images=[{'alt': f'anh {i}'} for i in range(4)],
        research={'serp': [{'link': 'https://vd.vn'}]},
    )


def test_bo_du_lieu_chuan_thi_PASS():
    kq = QAPipeline().run(**_bo_dat())
    assert kq['status'] == 'PASS', kq['blockers']


@pytest.mark.parametrize('ten_phep,be', [
    # Theme da render tieu de thanh H1; mot H1 nua trong post_content la
    # trang co HAI H1 va tieu de hien ra hai lan.
    ('h1_duy_nhat',            lambda d: d.update(html_body=d['html_body'] + '<h1>tieu de lap</h1>')),
    ('phu_tu_khoa',            lambda d: d['article'].update(body='Tủ lạnh kêu to. ' * 500)),
    ('faq',                    lambda d: d['article'].update(body=d['article']['body'].replace('Câu hỏi thường gặp', 'Kết luận'))),
    ('khong_khang_dinh_cam',   lambda d: d['article'].update(body=d['article']['body'] + ' Chỉ từ 150.000đ.')),
    ('anh_du_va_co_alt',       lambda d: d['images'].__setitem__(0, {'alt': ''})),
    ('anh_da_chen',            lambda d: d.update(html_body=d['html_body'].replace('ficool-article-image', 'x', 2))),
    ('co_nguon',               lambda d: d.update(research={})),
    ('boi_canh_dia_phuong',    lambda d: d['article'].update(body=d['article']['body'].replace('TP.HCM', 'nơi khác'))),
    ('lien_ket_noi_bo',        lambda d: d.update(html_body=d['html_body'].replace('/bang-gia/', 'https://doi-thu.vn/'))),
    ('khong_con_chu_thich_tho',lambda d: d.update(html_body=d['html_body'] + '<!-- INTERNAL: a | /b/ -->')),
    ('khong_lo_duong_dan_may', lambda d: d.update(html_body=d['html_body'] + '<img src="/tmp/anh.png">')),
    ('do_dai_title',           lambda d: d['article']['seo'].update(title='x' * 61)),
    ('do_dai_meta',            lambda d: d['article']['seo'].update(meta_description='y' * 161)),
    ('du_dai_bai',             lambda d: d['article'].update(body='# t\nNgắn quá. TP.HCM. Câu hỏi thường gặp. máy lạnh chảy nước trong nhà')),
])
def test_be_tung_phep_thi_cong_phai_DO(ten_phep, be):
    """Phép nào không thể đỏ thì không phải phép đo — đó là bài học từ check `cta`
    cũ (`đặt lịch|liên hệ|dịch vụ` luôn đúng trên site này)."""
    d = _bo_dat(); be(d)
    kq = QAPipeline().run(**d)
    assert kq['status'] == 'BLOCK', f'be {ten_phep} ma cong van PASS'
    assert ten_phep in kq['blockers'], f'be {ten_phep} nhung blockers la {kq["blockers"]}'
