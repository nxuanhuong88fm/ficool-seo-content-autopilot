"""slugify và bo_dau.

Lỗi nằm sẵn từ đầu: `unicodedata.normalize('NFKD','đ')` KHÔNG phân rã chữ đ,
rồi `.encode('ascii','ignore')` vứt luôn ký tự. 43/108 chủ đề có chữ đ trong
tiêu đề, nên 43 slug bị méo — có cái mất hẳn từ đầu:

    'tủ đông đóng tuyết dày'      -> tu-ong-ong-tuyet-day
    'đặt máy sấy chồng máy giặt'  -> at-may-say-chong-may-giat

`bo_dau()` trong CÙNG file xử lý đ đúng. Cùng một lỗi, trước đây chỉ sửa một nửa.
"""
from __future__ import annotations
import pytest

from pipeline.topic_selector import TopicSelector
from pipeline.utils import bo_dau, slugify


@pytest.mark.parametrize('vao,ra', [
    ('quạt điều hòa không mát', 'quat-dieu-hoa-khong-mat'),
    ('tủ đông đóng tuyết dày', 'tu-dong-dong-tuyet-day'),
    ('đặt máy sấy chồng máy giặt', 'dat-may-say-chong-may-giat'),
    ('di dời máy lạnh', 'di-doi-may-lanh'),
    ('Máy lạnh chảy nước', 'may-lanh-chay-nuoc'),
    ('Đ Đ Đ', 'd-d-d'),
])
def test_slugify_giu_chu_d(vao, ra):
    assert slugify(vao) == ra


def test_bo_dau_va_slugify_nhat_quan_ve_chu_d():
    """Hai hàm cùng file, cùng việc bỏ dấu — không được xử lý đ khác nhau."""
    for t in ('đông', 'điều', 'đặt', 'dời', 'Đông'):
        assert 'd' in bo_dau(t)
        assert 'd' in slugify(t), '%s -> %s' % (t, slugify(t))


def test_khong_slug_nao_cua_108_chu_de_bi_nuot_ky_tu():
    """Phép quét toàn bộ: mọi slug phải có đủ số 'từ' như tiêu đề."""
    for t in TopicSelector().all():
        s = slugify(t['title'])
        assert s, t['title']
        assert len(s.split('-')) == len(bo_dau(t['title']).split()), \
            'nuot ky tu: %r -> %r' % (t['title'], s)


def test_slugify_van_bo_ky_tu_khong_phai_chu():
    assert slugify('Máy lạnh: nguyên nhân & cách xử lý?') == 'may-lanh-nguyen-nhan-cach-xu-ly'
    assert slugify('  nhiều   khoảng   trắng  ') == 'nhieu-khoang-trang'
