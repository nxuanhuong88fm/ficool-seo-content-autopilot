"""Đồng phục nhất quán (③) và không sinh kỹ thuật viên nữ (④).

⚠️ ĐỌC TRƯỚC KHI TIN NHỮNG PHÉP Ở ĐÂY.

Phần lớn phép trong tệp này là PHÉP ĐO CHUỖI: chúng chứng minh prompt CÓ NÓI
điều gì, KHÔNG chứng minh model CÓ NGHE. Không có cách kiểm tự động nào rẻ để
biết trong ảnh sinh ra có logo Panasonic, kỹ thuật viên là nữ, hay chữ "Ficool"
bị vẽ méo — phát hiện những thứ đó cần thị giác.

Vì vậy ③ và ④ KHÔNG CÓ CỔNG MÁY. Chúng có prompt, có ảnh tham chiếu, và có
bước 0 "người xem từng ảnh" trong ke-hoach.json. Đừng để bảng test xanh ở đây
trông như một bảo đảm.

Ngoại lệ: hai phép cuối (`test_chi_vai_tro_co_nguoi_moi_nhan_anh_tham_chieu`,
`test_moi_ma_mau_deu_thuoc_token_da_duyet`) đo hành vi thật, không đo chuỗi.
"""
from __future__ import annotations

import pytest
import yaml

from pipeline.images import (CAM_NHAN_HIEU, CHU_DUOC_PHEP, KHONG_NGUOI, NHAN_VAT,
                             TEP_DONG_PHUC, ImagePipeline, cau_hinh_dong_phuc,
                             dung_prompt, mo_ta_dong_phuc)
from pipeline.topic_selector import TopicSelector

TOPIC = TopicSelector().by_id('ML-01')


def _ke_hoach():
    return ImagePipeline(provider=object()).plan(TOPIC)


def _theo_id(ma):
    return next(x for x in _ke_hoach() if x['id'] == ma)


# ── ④ không sinh kỹ thuật viên nữ ───────────────────────────────────────────
@pytest.mark.parametrize('ma', ['IMG-001', 'IMG-003', 'IMG-004'])
def test_moi_vai_tro_co_nguoi_deu_neu_ro_gioi_tinh(ma):
    """Gemini KHÔNG có tham số cấu hình cho việc này — `person_generation` chỉ
    nhận ALLOW_ALL/ALLOW_ADULT/ALLOW_NONE, tức là điều khiển CÓ hay KHÔNG có
    người, không điều khiển người đó là ai. Nên nó phải nằm trong prompt."""
    p = dung_prompt(_theo_id(ma))
    assert 'NAM' in p
    assert 'KHÔNG có kỹ thuật viên nữ' in p


def test_vai_tro_khong_nguoi_thi_noi_ro_la_khong_co_nguoi():
    p = dung_prompt(_theo_id('IMG-002'))
    assert KHONG_NGUOI in p
    assert NHAN_VAT not in p          # khong co nguoi thi khong can rang buoc nhan vat


# ── ③ đồng phục ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize('ma', ['IMG-001', 'IMG-003', 'IMG-004'])
def test_moi_vai_tro_co_nguoi_deu_mang_mo_ta_dong_phuc(ma):
    """Nếu chỉ IMG-004 mang ràng buộc thì ba ảnh còn lại có kỹ thuật viên mặc
    áo khác nhau — việc ③ hỏng ngay trong cùng một bài."""
    p = dung_prompt(_theo_id(ma))
    assert 'ĐỒNG PHỤC:' in p
    assert 'liền quần' in p            # khach chot kieu ao lien quan
    assert 'Ficool' in p               # khach chot CO chu tren ao


def test_vai_tro_khong_nguoi_thi_khong_cho_phep_chu_nao():
    """Không có người thì không có áo, nên không có chữ nào được phép."""
    p = dung_prompt(_theo_id('IMG-002'))
    assert CHU_DUOC_PHEP not in p
    assert 'không có chữ hay ký tự đọc được nào' in p


# ── cấm nhãn hiệu: nới chữ nhưng KHÔNG nới nhãn hiệu ────────────────────────
@pytest.mark.parametrize('ma', ['IMG-001', 'IMG-002', 'IMG-003', 'IMG-004'])
def test_moi_vai_tro_deu_cam_nhan_hieu_ben_thu_ba(ma):
    """Chỗ dễ trượt nhất: nới câu cấm chữ (để có "Ficool") mà lỡ nới luôn cấm
    nhãn hiệu. Đo trên ML-01 lượt đầu: 3/4 ảnh mang logo Mitsubishi/Panasonic."""
    p = dung_prompt(_theo_id(ma))
    assert CAM_NHAN_HIEU in p
    assert 'không tên hãng' in p


def test_cho_phep_chu_Ficool_nhung_van_cam_chu_khac():
    assert 'Ficool' in CHU_DUOC_PHEP
    assert 'không có chữ' in CHU_DUOC_PHEP or 'không chữ' in CHU_DUOC_PHEP


# ── hành vi thật, không phải đo chuỗi ───────────────────────────────────────
def test_chi_vai_tro_co_nguoi_moi_nhan_anh_tham_chieu(tmp_path, monkeypatch):
    """Truyền ảnh tham chiếu cho ảnh cận cảnh thiết bị là mời model nhét thêm
    một người vào cảnh không cần, và tốn token đầu vào vô ích."""
    import pipeline.images as pi

    mau = tmp_path / 'nhan-vat'
    mau.mkdir()
    (mau / 'a.webp').write_bytes(b'RIFF0000WEBPVP8 ')
    monkeypatch.setattr(pi, 'THU_MUC_THAM_CHIEU', mau)

    nhan = {}

    class _P:
        def generate(self, prompt, output_path, width=1600, height=900, anh_tham_chieu=()):
            nhan[output_path.name] = len(anh_tham_chieu)
            from connectors.image_provider import GeneratedImage
            output_path = output_path.with_suffix('.webp')
            output_path.parent.mkdir(parents=True, exist_ok=True)
            import io

            from PIL import Image
            im = Image.new('RGB', (1376, 768), (120, 140, 160))
            b = io.BytesIO(); im.save(b, 'WEBP', quality=85)
            output_path.write_bytes(b.getvalue())
            return GeneratedImage(output_path, 1376, 768, 'image/webp', 'gia',
                                  du_lieu=b.getvalue(), mime_tho='image/jpeg', byte_tho=1)

    pi.ImagePipeline(provider=_P()).generate(TOPIC, '', tmp_path)

    assert nhan['img-001'] == 1        # co nguoi
    assert nhan['img-002'] == 0        # KHONG co nguoi
    assert nhan['img-003'] == 1
    assert nhan['img-004'] == 1


def test_khong_co_anh_mau_thi_khong_no_ma_chay_binh_thuong(tmp_path, monkeypatch):
    """Khách chưa chọn phương án thì thư mục rỗng — pipeline vẫn phải chạy."""
    import pipeline.images as pi
    monkeypatch.setattr(pi, 'THU_MUC_THAM_CHIEU', tmp_path / 'khong-ton-tai')
    assert pi.anh_tham_chieu_dong_phuc() == ()


def test_moi_ma_mau_deu_thuoc_token_da_duyet():
    """Quy tắc dự án cấm đẻ giá trị thiết kế mới, và đồng phục là một quyết
    định thiết kế."""
    import re

    c = yaml.safe_load(TEP_DONG_PHUC.read_text(encoding='utf-8'))
    duoc_phep = {v.lower() for v in c['token_duoc_phep'].values()}
    tat_ca = set(re.findall(r'#[0-9a-fA-F]{6}', TEP_DONG_PHUC.read_text(encoding='utf-8')))
    la = {x.lower() for x in tat_ca} - duoc_phep
    assert not la, 'ma mau khong thuoc token da duyet: %s' % sorted(la)


def test_moi_phuong_an_chi_tham_chieu_token_co_that():
    c = cau_hinh_dong_phuc()
    tok = c['token_duoc_phep']
    for ten, pa in c['phuong_an'].items():
        for khoa in ('than_ao', 'nep_vai', 'chu'):
            v = pa.get(khoa)
            assert v is None or v in tok, '%s.%s = %r khong co trong token' % (ten, khoa, v)
    assert c['dang_dung'] in c['phuong_an']


def test_mo_ta_dong_phuc_dung_mau_that_cua_phuong_an():
    c = cau_hinh_dong_phuc()
    mo = mo_ta_dong_phuc('navy-nep-xanh')
    assert c['token_duoc_phep']['accent-900'] in mo      # than ao
    assert c['token_duoc_phep']['accent-500'] in mo      # nep vai
    assert 'Ficool' in mo


def test_doi_phuong_an_thi_mo_ta_doi_theo():
    """Nếu đổi `dang_dung` mà mô tả không đổi thì cấu hình chỉ là trang trí."""
    a = mo_ta_dong_phuc('navy-nep-xanh')
    b = mo_ta_dong_phuc('xanh-dam-tron')
    assert a != b
    assert 'Nẹp vai' in a and 'Nẹp vai' not in b        # phuong an nay khong co nep
