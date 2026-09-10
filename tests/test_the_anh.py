"""Thẻ `<img>` trong bài — class `wp-image`, `sizes`, và ưu tiên tải.

Vì sao đáng một tệp test riêng: đây là chỗ mất tốc độ lớn nhất, và nó KHÔNG
nhìn thấy được. Bài 383 đăng xong trông bình thường, nhưng mọi thiết bị đều tải
nguyên file 1376px vì thẻ thiếu một class.

`wp_filter_content_tags()` chỉ map `<img>` sang attachment khi thẻ có
`class="wp-image-{ID}"`. Đã kiểm chứng bằng đối chứng trên chính post 383:
thêm class vào là WordPress sinh ngay `srcset="…1376w, …1024w, …768w, …300w"`.
"""
from __future__ import annotations
import re
import tempfile
from pathlib import Path

import pytest

from connectors.wordpress.publishers import MOC_ANH, MOC_MEDIA_ID, CongBoHoSo
from pipeline.assembly import SIZES_BAI_VIET, AssemblyPipeline, _the_figure


def _anh(ma='IMG-001', loai='featured'):
    return {'id': ma, 'type': loai, 'alt': 'alt %s' % ma, 'caption': 'cap %s' % ma,
            'width': 1376, 'height': 768}


# ── class wp-image ──────────────────────────────────────────────────────────
def test_the_co_class_wp_image_khi_biet_media_id():
    the = _the_figure(_anh(), 'https://ficool.top/a.webp', 379)
    assert 'class="wp-image-379"' in the


def test_the_mang_moc_khi_chua_biet_media_id():
    """Đường ho-so chưa tải ảnh nên chưa có id — mốc để tác nhân thay."""
    the = _the_figure(_anh(), 'https://ficool.top/a.webp', '@@MEDIA_ID:IMG-001@@')
    assert 'class="wp-image-@@MEDIA_ID:IMG-001@@"' in the


def test_khong_co_ma_media_thi_khong_de_class_rong():
    """`class=""` rỗng là rác trong markup, không phải trạng thái hợp lệ."""
    the = _the_figure(_anh(), 'https://ficool.top/a.webp', None)
    assert 'class=""' not in the
    assert 'wp-image' not in the


# ── sizes ───────────────────────────────────────────────────────────────────
def test_the_tu_khai_sizes_theo_cot_720px():
    """Mặc định WordPress là `100vw` — sai cho cột 720px, trình duyệt sẽ chọn
    bản to hơn mức cần."""
    the = _the_figure(_anh(), 'u', 1)
    assert 'sizes="%s"' % SIZES_BAI_VIET in the
    assert '720px' in SIZES_BAI_VIET
    assert '100vw' in SIZES_BAI_VIET      # điện thoại vẫn cần toàn màn hình


# ── ưu tiên tải: ảnh đầu là LCP ─────────────────────────────────────────────
def test_anh_dai_dien_tai_ngay_vi_no_la_LCP():
    the = _the_figure(_anh(loai='featured'), 'u', 1)
    assert 'loading="eager"' in the and 'fetchpriority="high"' in the


def test_anh_con_lai_tai_lazy():
    the = _the_figure(_anh('IMG-003', 'instructional'), 'u', 1)
    assert 'loading="lazy"' in the and 'fetchpriority="low"' in the


def test_khong_duoc_lazy_ca_bon(tmp_path):
    """Gắn lazy cho ảnh ngay sau H1 là tự trì hoãn chính phần tử quyết định LCP."""
    imgs = [_anh('IMG-001', 'featured'), _anh('IMG-002', 'instructional'),
            _anh('IMG-003', 'instructional'), _anh('IMG-004', 'service')]
    than = '# T\n\n' + '\n\n'.join('<!-- IMAGE: %s -->' % a['id'] for a in imgs)
    up = [{**a, 'source_url': 'https://ficool.top/%s.webp' % a['id'], 'media_id': 100 + i}
          for i, a in enumerate(imgs)]
    h = AssemblyPipeline().run({'body': than}, imgs, up, tmp_path)

    assert h.count('loading="eager"') == 1, 'phai co dung MOT anh eager'
    assert h.count('loading="lazy"') == 3


# ── đi hết đường: mốc phải khớp kế hoạch ────────────────────────────────────
def test_duong_ho_so_sinh_du_hai_moc_va_ke_hoach_khop(tmp_path):
    import json

    cb = CongBoHoSo(tmp_path)
    imgs = []
    for i in (1, 2):
        p = tmp_path / 'images' / ('img-%03d.webp' % i)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'RIFF0000WEBPVP8 ')
        imgs.append({**_anh('IMG-%03d' % i, 'featured' if i == 1 else 'instructional'),
                     'local_path': str(p), 'filename': p.name, 'title': 't'})

    up = cb.tai_anh(imgs)
    assert all(u['source_url'] == MOC_ANH.format(id=u['id']) for u in up)
    assert all(u['media_id_moc'] == MOC_MEDIA_ID.format(id=u['id']) for u in up)

    than = '# T\n\n<!-- IMAGE: IMG-001 -->\n\n<!-- IMAGE: IMG-002 -->'
    h = AssemblyPipeline().run({'body': than}, imgs, up, tmp_path)
    kq = cb.dang_ban_nhap({'category': 'c', 'tags': [], 'primary_keyword': 'k', 'title': 't'},
                          {'slug': 's', 'seo': {'title': 't', 'meta_description': 'm'}}, h, up)

    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))
    # MOI moc trong HTML phai co muc tuong ung trong ke hoach — thieu mot cai la
    # tac nhan de lai @@MEDIA_ID: nguyen trong bai da dang.
    for a in kh['anh']:
        assert a['moc_thay_the'] in h, a['id']
        assert a['moc_media_id'] in h, a['id']
    assert any('@@MEDIA_ID:' in x for x in kh['kiem_sau_dang'])
    assert any('srcset' in x for x in kh['kiem_sau_dang'])


def test_buoc_0_liet_ke_du_bon_dieu_phai_xac_nhan_bang_mat(tmp_path):
    import json

    cb = CongBoHoSo(tmp_path)
    kq = cb.dang_ban_nhap({'category': 'c', 'tags': [], 'primary_keyword': 'k', 'title': 't'},
                          {'slug': 's', 'seo': {'title': 't', 'meta_description': 'm'}},
                          '<h1>x</h1>', [])
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))
    b0 = [b for b in kh['buoc'] if b['thu_tu'] == 0][0]

    ds = ' | '.join(b0['phai_xac_nhan']).lower()
    assert 'nam' in ds                    # ④ khong sinh ky thuat vien nu
    assert 'ficool' in ds                 # ③ chu tren ao
    assert 'lien quan' in ds              # ③ kieu dong phuc
    assert 'logo' in ds or 'ten hang' in ds


def test_demo_cung_sinh_dung_mot_anh_eager(tmp_path, monkeypatch):
    """Demo phải đo được hành vi LCP, không chỉ chạy cho có.

    Bản cũ tự dựng danh sách ảnh riêng, thiếu khoá `type`, nên KHÔNG ảnh nào là
    `featured` và demo cho eager/lazy = 0/4 — tức là nó chạy xanh mà không hề
    chạm tới thứ đang cần bảo vệ.
    """
    import pipeline.cli as cli
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    assert cli.main(['demo', 'may lanh chay nuoc']) == 0

    h = (tmp_path / 'output/demo/may-lanh-chay-nuoc/goi-dang/noi-dung.html').read_text(
        encoding='utf-8')
    assert h.count('loading="eager"') == 1
    assert h.count('loading="lazy"') == 3
    assert len(re.findall(r'class="wp-image-', h)) == 4
    assert len(set(re.findall(r'alt="([^"]+)"', h))) == 4      # 4 alt KHAC nhau


# ── H1: theme đã render tiêu đề, post_content không được lặp lại ────────────
def test_html_bai_viet_KHONG_con_h1(tmp_path):
    """Template bài viết (Bricks #268, `ps1h1`) render `{post_title}` thành H1.
    Giữ thêm một H1 trong post_content là trang có HAI H1 và tiêu đề hiện ra hai
    lần ngay dưới nhau — thấy trên bản xem thử 10/09, có ở 20/20 bài đã đăng.
    """
    h = AssemblyPipeline().run({'body': '# Tiêu đề bài\n\nĐoạn mở.'}, [], [], tmp_path)
    assert '<h1' not in h
    assert 'Đoạn mở' in h


def test_van_giu_h2_h3(tmp_path):
    """Bỏ H1 mà bỏ luôn H2 là xoá mất cấu trúc mục của bài."""
    than = '# T\n\n## Mục hai\n\nNội dung.\n\n### Mục ba\n\nNữa.'
    h = AssemblyPipeline().run({'body': than}, [], [], tmp_path)
    assert '<h2' in h and '<h3' in h


def test_chi_bo_h1_DAU_bai():
    """Một H1 nằm giữa bài là lỗi của người viết, không im lặng dọn hộ —
    cổng QA phải còn thấy nó."""
    from pipeline.assembly import BO_H1
    assert BO_H1.sub('', 'truoc<h1>x</h1>', count=1) == 'truoc<h1>x</h1>'
