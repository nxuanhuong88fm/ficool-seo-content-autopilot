from __future__ import annotations

from connectors.image_provider import GeminiImageProvider
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
        'canh': 'toàn cảnh bối cảnh của chủ đề trong một căn nhà Việt Nam',
        # KHONG ghep dinh ngu chi noi chon sau {chu_de}: nhieu tieu de da ket thuc
        # bang 'trong nha' -> 'trong nha trong nha o TP.HCM'. Dat truoc, khong dat sau.
        'mau_alt': 'Tổng quan: {chu_de}',
    },
    {
        'id': 'IMG-002', 'type': 'instructional', 'placement': 'after_h2_1',
        'purpose': 'show_problem',
        'canh': 'cận cảnh dấu hiệu của sự cố trên thiết bị',
        'mau_alt': 'Cận cảnh dấu hiệu {chu_de}',
    },
    {
        'id': 'IMG-003', 'type': 'instructional', 'placement': 'after_h2_2',
        'purpose': 'show_inspection',
        'canh': 'cảnh kiểm tra thiết bị một cách an toàn, đã ngắt nguồn điện',
        'mau_alt': 'Kiểm tra an toàn khi gặp {chu_de}',
    },
    {
        'id': 'IMG-004', 'type': 'service', 'placement': 'before_cta',
        'purpose': 'show_service_context',
        'canh': 'kỹ thuật viên điện lạnh mặc đồng phục xanh navy TRƠN đang làm việc tại nhà khách',
        'mau_alt': 'Kỹ thuật viên điện lạnh xử lý tại nhà ở {dia_phuong}',
    },
]

# Phần địa phương có thể đã dính sẵn trong tiêu đề chủ đề; dán chồng lần nữa ra
# 'tại TP.HCM tại TP.HCM' — đúng thứ đo được ở alt của IMG-004 bản cũ.
DUOI_DIA_PHUONG = (' tại TP.HCM', ' tại TP. HCM', ' tại Hồ Chí Minh', ' tại Sài Gòn')

# ⚠️ RÀNG BUỘC NHÃN HIỆU — đo được trên lượt sinh ML-01 đầu tiên (09/09/2026).
#
# Prompt cũ chỉ ghi "no text, watermark or invented logos" và model BỎ QUA:
#   IMG-001  logo Mitsubishi (ba viên kim cương đỏ) thêu trên ngực đồng phục
#   IMG-002  chữ "Panasonic" in rõ trên mặt dàn lạnh, kèm mã model
#   IMG-004  tên hãng trên mặt máy + chữ thêu vô nghĩa trên áo + lịch có chữ
#
# Ba trên bốn ảnh mang nhãn hiệu bên thứ ba. Đăng lên ficool.top là ngụ ý Ficool
# có liên kết với hãng đó — sai sự thật về doanh nghiệp, và là vấn đề nhãn hiệu.
#
# Bản dưới đây nêu ràng buộc THẲNG và CỤ THỂ, đo lại thì mặt máy trơn, không chữ
# đọc được. NHƯNG không có gì bảo đảm tuyệt đối: model vẫn có thể vẽ nhãn bất kỳ
# lúc nào, và không có cách kiểm tự động nào rẻ. Vì vậy `ke-hoach.json` bắt buộc
# mang bước NGƯỜI XEM TỪNG ẢNH trước khi đăng. Xem RULES A117.
RANG_BUOC = (
    'RÀNG BUỘC BẮT BUỘC: mọi thiết bị trong ảnh KHÔNG mang nhãn hiệu — mặt trước trơn, '
    'không tên hãng, không mã model, không tem nhãn, không sticker. '
    'Đồng phục (nếu có người) màu trơn, KHÔNG phù hiệu, KHÔNG logo, KHÔNG chữ thêu. '
    'KHÔNG có bất kỳ chữ hay ký tự đọc được nào trong khung hình, kể cả trên lịch, '
    'bao bì hay biển hiệu phía sau.'
)


def _gon(cum: str) -> str:
    cum = str(cum).strip().rstrip('?').strip()
    for x in DUOI_DIA_PHUONG:
        if cum.lower().endswith(x.lower()):
            return cum[: -len(x)].strip()
    return cum


class ImagePipeline:
    def __init__(self, provider=None):
        self.provider = provider or GeminiImageProvider()

    def plan(self, topic):
        chu_de = _gon(topic['title'])
        ra = []
        for v in VAI_TRO:
            alt = v['mau_alt'].format(chu_de=chu_de[0].lower() + chu_de[1:] if chu_de else '',
                                      dia_phuong=DIA_PHUONG) + ' – Ficool'
            ra.append({**v, 'subject': chu_de, 'alt': alt, 'title': alt,
                       'caption': 'Hình minh họa: %s.' % alt.replace(' – Ficool', '')})
        return ra

    def generate(self, topic, article, output_dir):
        rows = []
        for item in self.plan(topic):
            prompt = (
                'Ảnh biên tập chân thực cho bài viết tiếng Việt về điện lạnh gia dụng. '
                "Chủ đề: %s. Nội dung ảnh: %s. "
                'Bối cảnh: nhà ở tại %s, Việt Nam. '
                'Phong cách tài liệu chuyên nghiệp, thiết bị thực tế, thao tác an toàn, '
                'ánh sáng tự nhiên. '
                % (item['subject'], item['canh'], DIA_PHUONG) + RANG_BUOC
            )
            a = self.provider.generate(prompt=prompt,
                                       output_path=output_dir / 'images' / item['id'].lower(),
                                       width=1600, height=900)
            rows.append({**item, 'filename': a.path.name, 'width': a.width, 'height': a.height,
                         'mime_type': a.mime_type, 'provider': a.provider})
        dump_yaml(output_dir / 'image-manifest.yaml', {'topic_id': topic['id'], 'images': rows})
        return rows
