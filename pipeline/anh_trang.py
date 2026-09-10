"""Ảnh cho TRANG (trang chủ + 15 trang dịch vụ), khác với ảnh bài blog.

Vì sao là module riêng chứ không nhét vào `images.py`: ảnh bài blog có **bốn vai
trò cố định** sinh ra từ chủ đề bài, còn ảnh trang là **một ảnh cho một đích cụ
thể**, cảnh do người viết ra và nằm trong bản vẽ. Trộn hai thứ lại thì `plan()`
phải nhận thêm một cờ "đây là trang hay bài", và mọi phép đo của `images.py`
phải nhận thêm nhánh.

Dùng chung với ảnh bài: đồng phục, ràng buộc nhân vật, cấm nhãn hiệu, cấm chữ.
Đó là những thứ phải giống nhau trên MỌI ảnh của site.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from pipeline.anh_xu_ly import cat_og, sang_webp
from pipeline.images import (CAM_NHAN_HIEU, DIA_PHUONG, NHAN_VAT,
                             anh_tham_chieu_dong_phuc, mo_ta_dong_phuc)

TEP = Path(__file__).resolve().parents[1] / 'config/anh-trang.yaml'


class DichSai(ValueError):
    pass


def cau_hinh() -> dict:
    return yaml.safe_load(TEP.read_text(encoding='utf-8'))


def danh_sach(loc=()) -> list:
    """Trả về danh sách đích, mỗi đích đã có `ti_le` giải sẵn.

    `loc` rỗng nghĩa là lấy hết. Mã không có trong cấu hình thì báo NGAY chứ
    không lặng lẽ sinh thiếu — sinh thiếu chỉ lộ ra sau khi đã tiêu tiền.
    """
    c = cau_hinh()
    ra = []
    for d in c['dich']:
        ra.append({**d, 'ti_le': c['ti_le'][d.get('loai', 'dich_vu')]})

    if not loc:
        return ra
    co = {d['ma'] for d in ra}
    la = [x for x in loc if x not in co]
    if la:
        raise DichSai('khong co dich: %s. Co san: %s'
                      % (', '.join(la), ', '.join(sorted(co))))
    return [d for d in ra if d['ma'] in set(loc)]


def dung_prompt(dich: dict) -> str:
    """Prompt cho một ảnh trang.

    ⚠️ Mọi ảnh trên site đi qua `.halftone` = grayscale(.35) contrast(1.15).
    Nên phải yêu cầu ảnh đọc được khi BẠC MÀU — bố cục và tương phản sáng-tối,
    không dựa vào màu. Bỏ câu này thì ảnh nào cũng "đẹp" lúc xem file gốc rồi
    xám nhoè khi lên trang, và ta chỉ biết sau khi đã sinh đủ 16 tấm.
    """
    return ' '.join([
        'Ảnh biên tập chân thực, phong cách phóng sự dịch vụ tại nhà.',
        'Nội dung ảnh: %s.' % dich['canh'].strip().rstrip('.'),
        'Bối cảnh: nhà ở hoặc cửa hàng nhỏ tại %s, Việt Nam.' % DIA_PHUONG,
        'Ánh sáng tự nhiên, thao tác an toàn, thiết bị thực tế, không dàn dựng quá mức.',
        'Ảnh sẽ được phủ filter GIẢM BÃO HOÀ khi lên web: bố cục phải rõ nhờ '
        'tương phản sáng-tối và hình khối, KHÔNG dựa vào màu sắc rực rỡ.',
        NHAN_VAT,
        mo_ta_dong_phuc(kem_chu_nguc=False),
        # ⚠️ NHÃN NGỰC ĐỂ TRỐNG, KHÔNG CHỮ — đây là quyết định, không phải thiếu sót.
        #
        # Ở ảnh trang, kỹ thuật viên chỉ chiếm một phần khung nên nhãn ngực còn
        # vài chục pixel. Lượt sinh đầu (09/09) model viết ra "Fiesal". A118 đã
        # đo: chữ trong ảnh sinh ra là xổ số, siết prompt không chữa được. Mà một
        # nhãn trắng TRƠN thì không có gì để sai — nó vẫn đọc ra là đồng phục có
        # phù hiệu, và để ngỏ đường ghép logo thật lên sau.
        #
        # Vì vậy ảnh trang KHÔNG dùng `CHU_DUOC_PHEP` (câu cho phép chữ "Ficool");
        # nó cấm mọi chữ, giống vai trò ảnh không người bên `images.py`.
        'Ngực TRÁI áo có MỘT miếng nhãn nhỏ hình chữ nhật nền TRẮNG, BỎ TRỐNG '
        'hoàn toàn — không chữ, không logo, không hoa văn. Ngực phải để trống. '
        'Không có nhãn hay chữ nào trên tay áo, vai áo hay quần.',
        'CHỮ: KHÔNG có chữ hay ký tự đọc được nào trong toàn khung hình — không '
        'trên áo, thiết bị, lịch tường, bao bì hay biển hiệu phía sau.',
        CAM_NHAN_HIEU,
    ])


def _co(ti_le: str) -> tuple:
    """Đổi '4:3' thành (rộng, cao) để `ti_le_gan_nhat` chọn lại đúng chuỗi đó."""
    a, b = ti_le.split(':')
    return int(a) * 100, int(b) * 100


def sinh(provider, dich: dict, thu_muc: Path) -> dict:
    """Sinh MỘT ảnh trang + bản og, trả về bản ghi để ghi vào sổ."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    rong, cao = _co(dich['ti_le'])
    a = provider.generate(prompt=dung_prompt(dich), output_path=thu_muc / dich['ma'],
                          width=rong, height=cao,
                          anh_tham_chieu=anh_tham_chieu_dong_phuc())

    og = thu_muc / (dich['ma'] + '-og.webp')
    og.write_bytes(sang_webp(cat_og(a.du_lieu)))

    return {'ma': dich['ma'], 'ten': dich['ten'], 'url': dich['url'],
            'alt': dich['alt'], 'ti_le': dich['ti_le'],
            'tep': a.path.name, 'rong': a.width, 'cao': a.height,
            'byte': a.path.stat().st_size, 'tep_og': og.name,
            'byte_og': og.stat().st_size}
