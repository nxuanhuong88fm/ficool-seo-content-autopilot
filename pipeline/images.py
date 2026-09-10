from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from connectors.image_provider import GeminiImageProvider
from pipeline import anh_xu_ly
from pipeline.utils import dump_yaml

DIA_PHUONG = 'TP.HCM'

# Bốn vai trò KHÁC NHAU.
#
# Bản cũ lấy subject của IMG-001/002/003 lần lượt từ topic['title'],
# topic['primary_keyword'] và secondary_keywords[0] — mà cả ba chuỗi đó gần như
# trùng nhau, vì `primary_keyword` CHÍNH LÀ tiêu đề viết thường và
# `secondary_keywords[0]` cũng vậy (xem topic_selector.py:29).
#
# Đo trên bài ML-01 thật: ba ảnh cùng prompt, cùng alt. Ba tấm ảnh na ná nhau
# trong một bài vừa phí tiền sinh, vừa là alt trùng lặp — hại cho SEO ảnh, và
# vô ích cho người dùng trình đọc màn hình.
VAI_TRO = [
    {
        'id': 'IMG-001', 'type': 'featured', 'placement': 'after_h1',
        'purpose': 'establish_topic',
        'canh': 'toàn cảnh: kỹ thuật viên đang xem xét thiết bị trong một căn nhà Việt Nam',
        'co_nguoi': True,
        # KHONG ghep dinh ngu chi noi chon sau {chu_de}: nhieu tieu de da ket thuc
        # bang 'trong nha' -> 'trong nha trong nha o TP.HCM'. Dat truoc, khong dat sau.
        'mau_alt': 'Tổng quan: {chu_de}',
    },
    {
        'id': 'IMG-002', 'type': 'instructional', 'placement': 'after_h2_1',
        'purpose': 'show_problem',
        'canh': 'cận cảnh dấu hiệu của sự cố trên thiết bị, không có người trong khung',
        'co_nguoi': False,
        'mau_alt': 'Cận cảnh dấu hiệu {chu_de}',
    },
    {
        'id': 'IMG-003', 'type': 'instructional', 'placement': 'after_h2_2',
        'purpose': 'show_inspection',
        'canh': 'kỹ thuật viên kiểm tra thiết bị một cách an toàn, đã ngắt nguồn điện',
        'co_nguoi': True,
        'mau_alt': 'Kiểm tra an toàn khi gặp {chu_de}',
    },
    {
        'id': 'IMG-004', 'type': 'service', 'placement': 'before_cta',
        'purpose': 'show_service_context',
        'canh': 'kỹ thuật viên điện lạnh đang làm việc tại nhà khách',
        'co_nguoi': True,
        'mau_alt': 'Kỹ thuật viên điện lạnh xử lý tại nhà ở {dia_phuong}',
    },
]

# Phần địa phương có thể đã dính sẵn trong tiêu đề chủ đề; dán chồng lần nữa ra
# 'tại TP.HCM tại TP.HCM' — đúng thứ đo được ở alt của IMG-004 bản cũ.
DUOI_DIA_PHUONG = (' tại TP.HCM', ' tại TP. HCM', ' tại Hồ Chí Minh', ' tại Sài Gòn')

# ⚠️ RÀNG BUỘC — đo được trên lượt sinh ML-01 đầu tiên (09/09/2026).
#
# Prompt cũ chỉ ghi "no text, watermark or invented logos" và model BỎ QUA:
#   IMG-001  logo Mitsubishi (ba viên kim cương đỏ) thêu trên ngực đồng phục
#   IMG-002  chữ "Panasonic" in rõ trên mặt dàn lạnh, kèm mã model
#   IMG-004  tên hãng trên mặt máy + chữ thêu vô nghĩa trên áo + lịch có chữ
#
# Ba trên bốn ảnh mang nhãn hiệu bên thứ ba. Đăng lên ficool.top là ngụ ý Ficool
# có liên kết với hãng đó — sai sự thật về doanh nghiệp, và là vấn đề nhãn hiệu.
#
# Tách làm ba mảnh vì chúng nới/siết ĐỘC LẬP với nhau. Bản gộp trước đây cấm
# "không có bất kỳ chữ nào trong khung hình", mâu thuẫn trực tiếp với yêu cầu
# có chữ "Ficool" trên áo — không nới được nếu không tách.
CAM_NHAN_HIEU = (
    'CẤM NHÃN HIỆU: mọi thiết bị trong ảnh KHÔNG mang nhãn hiệu — mặt trước trơn, '
    'không tên hãng, không mã model, không tem nhãn, không sticker năng lượng. '
    'Không có logo của bất kỳ hãng nào trên thiết bị, đồng phục hay vật dụng.'
)

# ⚠️ Đây là chỗ NỚI so với bản cũ, và nới đúng chỗ model hay trượt nhất.
# Bù lại bằng bước 0 "người xem từng ảnh" trong ke-hoach.json.
CHU_DUOC_PHEP = (
    'CHỮ: chữ đọc được DUY NHẤT trong khung hình là từ "Ficool" trên ngực áo '
    'đồng phục, viết đúng chính tả, chữ in rõ ràng. Ngoài từ đó, không có chữ '
    'hay ký tự nào khác: không chữ trên thiết bị, lịch tường, bao bì hay biển '
    'hiệu phía sau.'
)

# Yêu cầu ④ của khách. Gemini KHÔNG có tham số cấu hình cho việc này —
# `person_generation` chỉ nhận ALLOW_ALL / ALLOW_ADULT / ALLOW_NONE, tức là
# điều khiển CÓ hay KHÔNG có người, không điều khiển người đó là ai.
# Nên ràng buộc phải nằm trong prompt, và được ảnh tham chiếu củng cố thêm.
NHAN_VAT = (
    'NHÂN VẬT: kỹ thuật viên là NAM, khoảng 25–40 tuổi, người Việt. '
    'KHÔNG có kỹ thuật viên nữ trong khung hình.'
)

TEP_DONG_PHUC = Path(__file__).resolve().parents[1] / 'config/dong-phuc.yaml'
THU_MUC_THAM_CHIEU = Path(__file__).resolve().parents[1] / 'knowledge/brand/nhan-vat'


def anh_tham_chieu_dong_phuc() -> tuple:
    """Ảnh mẫu đồng phục đã chốt. Rỗng khi khách chưa chọn phương án.

    Giới hạn 4 tệp: `gemini-3.1-flash-image` nhận tối đa 4 ảnh tham chiếu
    nhân vật.
    """
    if not THU_MUC_THAM_CHIEU.is_dir():
        return ()
    return tuple(sorted(p for p in THU_MUC_THAM_CHIEU.iterdir()
                        if p.suffix.lower() in ('.webp', '.png', '.jpg', '.jpeg'))[:4])


@lru_cache(maxsize=1)
def cau_hinh_dong_phuc() -> dict:
    return yaml.safe_load(TEP_DONG_PHUC.read_text(encoding='utf-8'))


def mo_ta_logo(vi_tri: str = 'nguc') -> str:
    """Mô tả logo lấy từ chính SVG đang dùng trên web, sau khi render ra và NHÌN."""
    lg = cau_hinh_dong_phuc()['logo']
    goc = next(g for g in cau_hinh_dong_phuc()['goc_chup'] if g['logo'] == vi_tri)
    phan = ['LOGO: %s' % lg['cau_truc'].strip()]
    if lg.get('ban_mau', {}).get(vi_tri):
        phan.append('MÀU LOGO: %s' % lg['ban_mau'][vi_tri].strip())
    if vi_tri == 'lung':
        phan.append('Dòng tagline ghi đúng: "%s".' % lg['tagline'])
    else:
        phan.append('Bản này KHÔNG có dòng tagline.')
    phan.append('Vị trí: %s.' % goc['vi_tri_logo'].strip())
    if lg.get('rang_buoc'):
        phan.append(lg['rang_buoc'].strip())
    return ' '.join(phan)


def anh_logo(vi_tri: str = 'nguc'):
    """Đường dẫn ảnh logo đã tô theo màu áo, dùng làm ảnh tham chiếu."""
    duong = Path(__file__).resolve().parents[1] /         cau_hinh_dong_phuc()['logo']['anh_tham_chieu'][vi_tri]
    return (duong,) if duong.exists() else ()


def mo_ta_dong_phuc(ten_phuong_an: str | None = None, kem_chu_nguc: bool = True) -> str:
    """Dựng câu mô tả đồng phục từ cấu hình, không hardcode màu trong mã.

    `kem_chu_nguc=False` bỏ câu "trên ngực trái thêu chữ Ficool màu trắng".
    Dùng khi nơi gọi TỰ tả phần ngực áo theo cách khác — mẫu đã chốt mang một
    MIẾNG NHÃN NỀN TRẮNG chữ xanh, không phải chữ trắng thêu thẳng lên áo. Để cả
    hai câu trong một prompt là đưa cho model hai chỉ dẫn đá nhau, và đó đúng là
    chỗ nó trượt (RULES A118/A119).
    """
    c = cau_hinh_dong_phuc()
    pa = c['phuong_an'][ten_phuong_an or c['dang_dung']]
    tok = c['token_duoc_phep']
    kieu = c.get('kieu_trang_phuc', {}).get(pa.get('kieu', ''), '')
    phan = ['ĐỒNG PHỤC: %s' % (('%s. %s' % (kieu.capitalize(), pa['mo_ta'].strip()))
                               if kieu else pa['mo_ta'].strip())]
    phan.append('Màu thân áo %s.' % tok[pa['than_ao']])
    if pa.get('nep_vai'):
        phan.append('Nẹp vai màu %s.' % tok[pa['nep_vai']])
    if kem_chu_nguc:
        ch = c['chu_nguc']
        phan.append('Trên %s thêu chữ "%s" màu %s.'
                    % (ch['vi_tri'], ch['noi_dung'], tok[pa['chu']]))
    return ' '.join(phan)


def _gon(cum: str) -> str:
    cum = str(cum).strip().rstrip('?').strip()
    for x in DUOI_DIA_PHUONG:
        if cum.lower().endswith(x.lower()):
            return cum[: -len(x)].strip()
    return cum


def _caption(alt: str) -> str:
    """Alt co the da bat dau bang mot nhan co dau hai cham ('Tong quan: ...').
    Ghep them 'Hinh minh hoa:' nua ra hai dau hai cham trong mot cau."""
    than = alt.replace(' – Ficool', '').strip()
    if ':' in than:
        return than.rstrip('.') + '.'
    return 'Hình minh họa: %s.' % than


KHONG_NGUOI = 'KHÔNG có người nào trong khung hình.'


def dung_prompt(item, phuong_an_dong_phuc=None) -> str:
    """Dựng prompt cho một vai trò ảnh.

    Ràng buộc đồng phục và nhân vật CHỈ gắn cho vai trò có người. Gắn cho ảnh
    cận cảnh thiết bị là mời model nhét thêm một người vào cảnh không cần.
    """
    phan = [
        'Ảnh biên tập chân thực cho bài viết tiếng Việt về điện lạnh gia dụng.',
        'Chủ đề: %s.' % item['subject'],
        'Nội dung ảnh: %s.' % item['canh'],
        'Bối cảnh: nhà ở tại %s, Việt Nam.' % DIA_PHUONG,
        'Phong cách tài liệu chuyên nghiệp, thiết bị thực tế, thao tác an toàn, ánh sáng tự nhiên.',
        CAM_NHAN_HIEU,
    ]
    if item.get('co_nguoi'):
        phan += [NHAN_VAT, mo_ta_dong_phuc(phuong_an_dong_phuc), CHU_DUOC_PHEP]
    else:
        # Không có người thì cũng không có áo, nên không có chữ nào được phép.
        phan += [KHONG_NGUOI, 'CHỮ: không có chữ hay ký tự đọc được nào trong khung hình.']
    return ' '.join(phan)


class ImagePipeline:
    def __init__(self, provider=None):
        self.provider = provider or GeminiImageProvider()

    def plan(self, topic):
        # Chủ đề của ẢNH lấy từ TỪ KHOÁ CHÍNH, không phải tiêu đề bài.
        # 80/108 tiêu đề trong bản đồ funnel có dấu hai chấm ("Máy giặt bị rò
        # nước: Những vị trí cần kiểm tra"). Nhét cả tiêu đề vào alt cho ra
        # "Tổng quan: máy giặt bị rò nước: Những vị trí..." — hai dấu hai chấm
        # trong một câu, và một alt dài gấp đôi mức cần. Từ khoá chính của khách
        # dài 4–9 từ và không tệp nào chứa dấu hai chấm.
        chu_de = _gon(topic.get('primary_keyword') or topic['title'])
        ra = []
        for v in VAI_TRO:
            alt = v['mau_alt'].format(chu_de=chu_de[0].lower() + chu_de[1:] if chu_de else '',
                                      dia_phuong=DIA_PHUONG) + ' – Ficool'
            ra.append({**v, 'subject': chu_de, 'alt': alt, 'title': alt,
                       'caption': _caption(alt)})
        return ra

    def generate(self, topic, article, output_dir):
        rows = []
        tham_chieu = anh_tham_chieu_dong_phuc()
        for item in self.plan(topic):
            # Ảnh tham chiếu nhân vật CHỈ cho vai trò có người. Đây là cơ chế ép
            # nhất quán mạnh hơn hẳn mô tả bằng chữ; `gemini-3.1-flash-image`
            # nhận tới 4 ảnh loại này.
            tc = tham_chieu if item.get('co_nguoi') else ()
            a = self.provider.generate(prompt=dung_prompt(item),
                                       output_path=output_dir / 'images' / item['id'].lower(),
                                       width=1600, height=900, anh_tham_chieu=tc)
            hang = {**item, 'filename': a.path.name, 'width': a.width, 'height': a.height,
                    'mime_type': a.mime_type, 'provider': a.provider}

            # Bản og CHỈ cho ảnh đại diện, và dẫn xuất từ CHÍNH khung vừa sinh —
            # không gọi API lần hai. Hai lượt gọi cho ra HAI TẤM ẢNH KHÁC NHAU,
            # nghĩa là ảnh đại diện và ảnh mở bài không còn là một cảnh.
            #
            # Vì sao cần bản riêng: ảnh đại diện không hiển thị trong trang bài
            # viết; nó chỉ dùng cho card chuyên mục và cho og:image. Chuẩn social
            # là 1200x630 (tỉ lệ 1,905), khác 16:9 (1,778) của ảnh gốc.
            if item.get('type') == 'featured':
                og = anh_xu_ly.cat_og(a.du_lieu)
                duong_og = a.path.with_name(a.path.stem + '-og.webp')
                duong_og.write_bytes(og)
                hang['bien_the'] = [{
                    'vai_tro': 'og', 'filename': duong_og.name,
                    'local_path': str(duong_og), 'mime_type': 'image/webp',
                    'width': anh_xu_ly.OG_RONG, 'height': anh_xu_ly.OG_CAO,
                    'alt': item['alt'],
                }]

            rows.append(hang)
        dump_yaml(output_dir / 'image-manifest.yaml', {'topic_id': topic['id'], 'images': rows})
        return rows
