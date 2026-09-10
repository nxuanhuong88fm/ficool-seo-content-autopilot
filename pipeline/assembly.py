from __future__ import annotations
import html
import re
from markdown import markdown
from pipeline.utils import dump_yaml

# Ghép neo ảnh và neo liên kết vào bài, rồi đổi Markdown -> HTML bằng thư viện
# chuẩn. KHÔNG tự viết bộ chuyển: bản tự viết trong scripts/production_draft.py
# sinh <li> không có <ul> bọc (HTML không hợp lệ), bỏ qua [neo](/url/) và **đậm**,
# và đổ nguyên bảng Markdown thành các đoạn <p>| ... |</p>.
# Mốc ảnh mang thêm MÔ TẢ tuỳ chọn sau dấu `|`:
#     <!-- IMAGE: IMG-002 -->                    mốc cũ, vẫn đọc được
#     <!-- IMAGE: IMG-002 | mô tả theo ngữ cảnh -->
# Mô tả là thứ tác nhân viết bài biết mà khuôn không biết: mục này đang nói về
# máng hứng nước thì ảnh phải là máng hứng nước, không phải "cận cảnh dấu hiệu
# của sự cố trên thiết bị" chung chung. Mốc không kèm mô tả thì lùi về khuôn.
MOC_ANH = re.compile(
    r'<!-- IMAGE:\s*(?P<id>[A-Za-z0-9_-]+)\s*(?:\|\s*(?P<mo_ta>[^>]*?)\s*)?-->')
MOC_LIEN_KET = re.compile(r'<!-- INTERNAL:\s*(?P<neo>.+?)\s*\|\s*(?P<url>\S+?)\s*-->')


def doc_mo_ta(than: str) -> dict:
    """Quét mô tả ảnh từ mốc trong thân bài: `{'IMG-002': 'mô tả', ...}`.

    Vì sao phải tách ra khỏi `AssemblyPipeline.run`: mô tả không chỉ đi vào HTML,
    nó còn phải đi vào `ke-hoach.json` — bước 0 bảo người ĐỌC TỪNG MÔ TẢ, mà đưa
    cho họ bản khuôn trong khi bài mang bản theo ngữ cảnh là đưa nhầm bản.
    """
    return {m.group('id'): (m.group('mo_ta') or '').strip()
            for m in MOC_ANH.finditer(than) if (m.group('mo_ta') or '').strip()}


# Khung nội dung bài viết là ĐÚNG 720 CSS px ở mọi màn hình >= 820px (trần cứng
# `max-width:720px` Bricks đặt trên thẻ ARTICLE). Mặc định `sizes` của WordPress
# là `100vw` — sai cho một cột 720px, trình duyệt sẽ chọn bản to hơn mức cần.
SIZES_BAI_VIET = '(max-width: 767px) 100vw, 720px'
# ⚠️ ĐO ĐƯỢC TRÊN BÀI 383 (09/09) — WordPress 6.7+ CHÈN THÊM `auto, ` vào đầu
# `sizes` của MỌI ảnh có `loading="lazy"`. HTML thật ra là:
#     anh eager (IMG-001): sizes="(max-width: 767px) 100vw, 720px"
#     ba ảnh lazy        : sizes="auto, (max-width: 767px) 100vw, 720px"
# Đây KHÔNG phải lỗi và không phải WordPress đè lên ta: `auto` bảo trình duyệt
# lấy đúng bề rộng dựng thật của thẻ, còn phần ta khai giữ nguyên phía sau làm
# đường lui cho trình duyệt chưa hiểu `auto`. Đừng "sửa" chỗ này.
# Hệ quả cho hậu kiểm: so `sizes` phải dùng CHỨA, không được dùng BẰNG.


def _the_giu_cho(anh):
    """Khối GIỮ CHỖ: chưa có ảnh, nhưng đã biết chỗ nào cần ảnh gì.

    Vì sao nhìn thấy được chứ không phải chú thích HTML ẩn: người điền ảnh làm
    việc trong wp-admin, và một chú thích `<!-- -->` thì họ không thấy. Bài đang
    `draft` và site đang `blog_public = 0` nên khối này hiện ra là CÓ ÍCH.

    Vì sao GIỮ class `ficool-article-image`: cổng QA `anh_da_chen` đếm đúng chuỗi
    đó (`pipeline/qa.py`). Đổi tên class là làm đỏ một cổng vì lý do sai.

    `data-anh-id` là chốt chặn — hậu kiểm dùng nó để không cho bài còn giữ chỗ
    lên bản công khai.
    """
    e = html.escape
    ti_le = '%s:%s' % (anh.get('ti_le_rong', 16), anh.get('ti_le_cao', 9))
    mo_ta = anh.get('mo_ta') or anh.get('canh') or ''
    return (
        '<figure class="ficool-article-image ficool-anh-giu-cho"'
        f' data-anh-id="{e(anh["id"])}"'
        f' data-vai-tro="{e(anh.get("type", ""))}"'
        f' data-ti-le="{e(ti_le)}"'
        f' data-alt="{e(anh["alt"])}">'
        '<div class="ficool-anh-giu-cho__nhan">'
        f'<b>CẦN ẢNH · {e(anh["id"])} · {e(ti_le)}</b>'
        f'<span>{e(mo_ta)}</span>'
        '</div>'
        '</figure>'
    )


def _the_figure(anh, nguon_url, ma_media=None):
    """Dựng thẻ figure cho một ảnh trong bài.

    `ma_media` là id attachment WordPress (hoặc mốc thay thế ở đường ho-so).
    KHÔNG BỎ ĐƯỢC: `wp_filter_content_tags()` chỉ map `<img>` sang attachment
    khi thẻ có `class="wp-image-{ID}"`. Thiếu class thì WordPress không chèn
    `srcset`, và điện thoại có cột 350px vẫn tải nguyên file 1376px.
    Đã kiểm chứng bằng đối chứng trên post 383.
    """
    lop = 'wp-image-%s' % ma_media if ma_media else ''

    # Ảnh đầu nằm ngay sau H1 nên nó là LCP. Gắn `lazy` cho nó là tự trì hoãn
    # chính phần tử quyết định điểm LCP.
    la_lcp = anh.get('type') == 'featured'
    tai = ('loading="eager" fetchpriority="high"' if la_lcp
           else 'loading="lazy" fetchpriority="low"')

    return (
        '<figure class="ficool-article-image">'
        f'<img src="{html.escape(nguon_url)}"'
        + (f' class="{lop}"' if lop else '')
        + f' alt="{html.escape(anh["alt"])}"'
        f' width="{anh["width"]}" height="{anh["height"]}"'
        f' sizes="{SIZES_BAI_VIET}" {tai} decoding="async">'
        f'<figcaption>{html.escape(anh["caption"])}</figcaption>'
        '</figure>'
    )


class AssemblyPipeline:
    def run(self, article, images, uploaded, output_dir):
        body = article['body']
        theo_id = {x['id']: x for x in images}
        da_tai = {x['id']: x for x in uploaded}

        # Quét mốc TRƯỚC khi thay: mô tả nằm trong mốc, mà mốc thì biến mất
        # ngay sau lượt thay đầu tiên.
        mo_ta_theo_id = {m.group('id'): (m.group('mo_ta') or '').strip()
                         for m in MOC_ANH.finditer(body)}

        for iid, anh in theo_id.items():
            nguon = da_tai.get(iid, anh)
            url = nguon.get('source_url') or nguon.get('local_path', '')
            if mo_ta_theo_id.get(iid):
                anh = {**anh, 'mo_ta': mo_ta_theo_id[iid]}

            # KHÔNG có URL nghĩa là chưa có ảnh -> dựng khối giữ chỗ. Một quyết
            # định ở một chỗ: `tai_anh` quyết định có ảnh hay không, `assembly`
            # chỉ đọc kết quả.
            fig = (_the_giu_cho(anh) if nguon.get('giu_cho') or not url
                   else _the_figure(anh, url,
                                    nguon.get('media_id') or nguon.get('media_id_moc')))

            # Khớp bằng regex chứ không bằng chuỗi: mốc có thể mang mô tả.
            moc = re.compile(r'<!-- IMAGE:\s*%s\s*(?:\|[^>]*?)?-->' % re.escape(iid))
            if moc.search(body):
                body = moc.sub(lambda m: fig, body, count=1)
            elif iid == 'IMG-001':
                # dùng hàm thay cho chuỗi: fig chứa dấu \ thì re.sub sẽ hiểu nhầm
                body = re.sub(r'^# .+$', lambda m: m.group(0) + '\n\n' + fig, body, count=1, flags=re.M)
            else:
                body += '\n\n' + fig + '\n'

        body = MOC_LIEN_KET.sub(lambda m: f'<a href="{m.group("url")}">{m.group("neo")}</a>', body)
        # Mốc ảnh thừa (model nhắc IMG-005 mà không có ảnh) phải bị gỡ, nếu không
        # nó lọt nguyên vào bài — cổng QA `khong_con_chu_thich_tho` sẽ bắt.
        body = MOC_ANH.sub('', body)

        html_body = markdown(body, extensions=['extra', 'tables'])
        dump_yaml(output_dir / 'assembled.yaml',
                  {'html_length': len(html_body), 'image_count': len(images)})
        (output_dir / 'article.html').write_text(html_body, encoding='utf-8')
        return html_body
