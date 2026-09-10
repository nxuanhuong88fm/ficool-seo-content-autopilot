"""Ảnh MƯỢN làm ảnh đại diện cho bài blog khi chưa có ảnh riêng.

Không sinh ảnh thì bài không có featured image, nghĩa là không có `og:image`
riêng. 107 bài cùng một thẻ chia sẻ là một cách tự bỏ phí — trong khi 16 ảnh
trang đã nằm sẵn trong Media Library và mỗi bài đã có sẵn danh mục thiết bị.

Hai tầng, tầng một dùng chính dữ liệu bản đồ funnel của khách:

    1. `topic['trang_dich_vu']`  -> ảnh của đúng trang đó   (67/108 bài)
    2. danh mục -> ảnh dịch vụ tiêu biểu                    (41 bài còn lại)

Bảng nằm trong `config/anh-muon.yaml` chứ không hardcode: đây là quyết định
biên tập, đổi nó không nên phải sửa mã — cùng lý do `dong-phuc.yaml` là YAML.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

TEP = Path(__file__).resolve().parents[1] / 'config/anh-muon.yaml'


class KhongCoAnhMuon(RuntimeError):
    pass


@lru_cache(maxsize=1)
def cau_hinh() -> dict:
    return yaml.safe_load(TEP.read_text(encoding='utf-8'))


def chon(topic: dict) -> dict:
    """Trả `{'anh': <id>, 'og': <id>, 'nguon': <lý do chọn>}`.

    Luôn trả về một cái gì đó: tầng cuối là hero trang chủ. Trả `None` ở đây
    nghĩa là 41 bài không có ảnh đại diện mà không ai biết — đúng loại lỗi im
    lặng mà kho này đã mất công dựng cổng để chặn.
    """
    c = cau_hinh()
    bang = c['theo_trang_dich_vu']

    # Tầng 1 — bản đồ funnel đã chỉ đích danh trang dịch vụ.
    dv = (topic.get('trang_dich_vu') or '').strip()
    if dv and dv in bang:
        return {**bang[dv], 'nguon': 'trang_dich_vu %s' % dv}

    # Tầng 2 — theo danh mục.
    tien_to = str(topic.get('id', '')).split('-')[0]
    if tien_to not in c['theo_danh_muc']:
        raise KhongCoAnhMuon(
            'khong biet danh muc %r cua chu de %r' % (tien_to, topic.get('id')))

    dv2 = c['theo_danh_muc'][tien_to]
    if dv2 and dv2 in bang:
        return {**bang[dv2], 'nguon': 'danh muc %s -> %s' % (tien_to, dv2)}

    # Tầng cuối — TK không có trang dịch vụ nào trên site.
    return {**c['hero_trang_chu'], 'nguon': 'hero trang chu (danh muc %s chua co trang dich vu)' % tien_to}


def gan_vao(images: list, topic: dict) -> list:
    """Gắn ảnh mượn vào vai trò `featured`, giữ nguyên ba vai trò còn lại.

    Vai trò `featured` là ảnh đại diện; nó KHÔNG hiển thị trong thân bài (đo
    được trên bài 383), nên mượn ảnh ở đây không làm bài trông lặp.
    """
    m = chon(topic)
    ra = []
    for x in images:
        if x.get('type') == 'featured':
            ra.append({**x, 'media_id': m['anh'], 'og_media_id': m['og'],
                       'anh_muon': True, 'anh_muon_nguon': m['nguon']})
        else:
            ra.append(x)
    return ra
