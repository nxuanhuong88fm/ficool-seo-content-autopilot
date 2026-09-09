from __future__ import annotations
import html
import re
from markdown import markdown
from pipeline.utils import dump_yaml

# Ghép neo ảnh và neo liên kết vào bài, rồi đổi Markdown -> HTML bằng thư viện
# chuẩn. KHÔNG tự viết bộ chuyển: bản tự viết trong scripts/production_draft.py
# sinh <li> không có <ul> bọc (HTML không hợp lệ), bỏ qua [neo](/url/) và **đậm**,
# và đổ nguyên bảng Markdown thành các đoạn <p>| ... |</p>.
MOC_ANH = re.compile(r'<!-- IMAGE:\s*(?P<id>[A-Za-z0-9_-]+)\s*-->')
MOC_LIEN_KET = re.compile(r'<!-- INTERNAL:\s*(?P<neo>.+?)\s*\|\s*(?P<url>\S+?)\s*-->')


def _the_figure(anh, nguon_url):
    return (
        '<figure class="ficool-article-image">'
        f'<img src="{html.escape(nguon_url)}" alt="{html.escape(anh["alt"])}"'
        f' width="{anh["width"]}" height="{anh["height"]}" loading="lazy">'
        f'<figcaption>{html.escape(anh["caption"])}</figcaption>'
        '</figure>'
    )


class AssemblyPipeline:
    def run(self, article, images, uploaded, output_dir):
        body = article['body']
        theo_id = {x['id']: x for x in images}
        da_tai = {x['id']: x for x in uploaded}

        for iid, anh in theo_id.items():
            nguon = da_tai.get(iid, anh)
            url = nguon.get('source_url') or nguon.get('local_path', '')
            fig = _the_figure(anh, url)
            moc = f'<!-- IMAGE: {iid} -->'
            if moc in body:
                body = body.replace(moc, fig, 1)
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
