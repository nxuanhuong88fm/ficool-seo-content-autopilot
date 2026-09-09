"""Ba đường đưa bài lên WordPress, sau MỘT giao diện.

Trục thật KHÔNG phải "MCP hay REST" — đo được là ability của novamira cũng đi qua
HTTP với cùng application password:

    POST /wp-json/novamira/v1/abilities/{ten}/run  -> 401 khi chưa đăng nhập
    permission_callback = novamira_rest_run_ability_permission (rest-shim.php:45)

Trục thật là hai câu hỏi khác nhau:

  (1) AI thực thi?  máy (Python, cần khoá)  ·  tác nhân (Claude Code, không cần)
  (2) API nào?      REST lõi (luôn có)      ·  ability novamira (giàu hơn)

  duong        | ai chay  | can khoa | duoc gi them
  -------------+----------+----------+--------------------------------------
  CongBoHoSo   | tac nhan | KHONG    | Rank Math + schema qua MCP
  CongBoNova   | may      | co       | meta Rank Math hang nhat
  CongBoRest   | may      | co       | chay o dau cung duoc

CẢNH BÁO THIẾT KẾ — vì sao KHÔNG dùng `rank-math-edit-post-schema`:

JSON-LD vẫn được CHÈN VÀO post_content ở cả ba đường. Đặt schema qua Rank Math
thì khối FAQPage nằm NGOÀI post_content, nên cổng QA sẽ chấm một tài liệu khác
với tài liệu được đăng — đúng lỗi đã sửa ở `run.py`. Một hành vi cho cả ba
đường, hoặc không gì cả.

`rank-math-edit-post-seo` (meta title/description) thì dùng, vì chỗ đó KHÔNG
trùng lặp: REST lõi phải ĐOÁN tên trường qua `WP_META_TITLE_FIELD`.
"""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from typing import Protocol

from .ability import NovamiraClient, NovamiraError
from .client import WordPressClient
from .posts import create_draft, ids_for_taxonomy
from .verify import verify_post

KHOA_WP = ('WP_URL', 'WP_USERNAME', 'WP_APPLICATION_PASSWORD')
MOC_ANH = '@@ANH:{id}@@'


class CongBo(Protocol):
    ten: str
    can_khoa: bool
    def san_sang(self) -> bool: ...
    def tai_anh(self, images) -> list: ...
    def don_anh(self, uploaded) -> None: ...
    def dang_ban_nhap(self, topic, article, html_body, uploaded) -> dict: ...


class CongBoRest:
    """REST lõi WordPress. Chạy ở đâu cũng được, kể cả không có plugin novamira."""

    ten = 'rest'
    can_khoa = True

    def __init__(self, client=None):
        self.client = client or WordPressClient()

    def san_sang(self) -> bool:
        return all(os.getenv(k) for k in KHOA_WP)

    def tai_anh(self, images):
        ra = []
        for it in images:
            wp = self.client.upload_media(it['local_path'], title=it['title'], alt_text=it['alt'],
                                          caption=it['caption'], description=it['caption'])
            ra.append({**it, 'media_id': wp['id'],
                       'source_url': wp.get('source_url') or wp.get('guid', {}).get('rendered', '')})
        return ra

    def don_anh(self, uploaded):
        for it in uploaded:
            try:
                self.client.delete_media(it['media_id'])
            except Exception:
                pass

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        slug = article['slug']
        trung = self.client.find_posts_by_slug(slug)
        if trung:
            raise RuntimeError('TRUNG SLUG: /%s/ da ton tai (post %s)'
                               % (slug, [p['id'] for p in trung]))

        meta = {}
        tf, df = os.getenv('WP_META_TITLE_FIELD', ''), os.getenv('WP_META_DESCRIPTION_FIELD', '')
        if tf:
            meta[tf] = article['seo'].get('title')
        if df:
            meta[df] = article['seo'].get('meta_description')

        post = create_draft(
            self.client, title=article['seo'].get('title') or topic['title'],
            content=html_body, slug=slug, excerpt=article['seo'].get('meta_description', ''),
            categories=ids_for_taxonomy(self.client, 'categories', [topic['category']]),
            tags=ids_for_taxonomy(self.client, 'tags', topic.get('tags', [])),
            featured_media=uploaded[0]['media_id'] if uploaded else None,
            meta=meta or None, author=os.getenv('WP_AUTHOR_ID') or None)

        v = verify_post(self.client, post['id'], 'draft')
        if not v['passed']:
            raise RuntimeError('XAC MINH HONG: %s' % (v,))
        return {'duong': self.ten, 'post_id': post['id'], 'status': v['status'],
                'link': v['link'], 'media': uploaded}


class CongBoNovamira(CongBoRest):
    """REST lõi cho ảnh và bài, ability novamira cho phần Rank Math.

    Cố ý KHÔNG chuyển ảnh/bài sang ability: đường REST đã chạy được và đã có
    test đầu-tới-cuối. Chỉ đổi đúng chỗ REST lõi phải đoán tên trường.
    """

    ten = 'novamira'

    def __init__(self, client=None, nova=None):
        super().__init__(client)
        self.nova = nova or NovamiraClient()

    def san_sang(self) -> bool:
        return super().san_sang() and self.nova.san_sang()

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        kq = super().dang_ban_nhap(topic, article, html_body, uploaded)
        seo = article['seo']
        try:
            self.nova.chay('novamira/rank-math-edit-post-seo', {
                'post_id': kq['post_id'],
                'seo_title': seo.get('title'),
                'meta_description': seo.get('meta_description'),
                'focus_keywords': [topic['primary_keyword']],
            })
            kq['rank_math'] = 'da ghi'
        except NovamiraError as e:
            # Bài đã tạo xong rồi. Hỏng ở đây là hỏng phần thêm, không phải
            # hỏng cả lượt — nên ghi lại chứ không ném lên.
            kq['rank_math'] = 'HONG: %s' % e
        return kq


class CongBoHoSo:
    """Không nói chuyện với WordPress. Ghi một gói đầy đủ để tác nhân đăng qua MCP.

    Vì sao cần đường này: MCP chỉ tồn tại trong phiên Claude Code; tiến trình
    Python không gọi được. Nên Python làm phần xác định được (viết, ghép, đo),
    rồi bàn giao phần cần quyền cho tác nhân — bên đã có sẵn quyền mà không cần
    một biến WP_* nào.
    """

    ten = 'ho-so'
    can_khoa = False

    def __init__(self, thu_muc):
        self.goc = Path(thu_muc)

    def san_sang(self) -> bool:
        return True

    def tai_anh(self, images):
        # Chưa lên WordPress nên URL còn là mốc; tác nhân thay sau khi tải ảnh.
        return [{**i, 'media_id': None, 'source_url': MOC_ANH.format(id=i['id'])} for i in images]

    def don_anh(self, uploaded):
        goi = self.goc / 'goi-dang'
        if goi.exists():
            shutil.rmtree(goi)

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        goi = self.goc / 'goi-dang'
        (goi / 'images').mkdir(parents=True, exist_ok=True)

        anh = []
        for it in uploaded:
            nguon = Path(it['local_path'])
            if nguon.exists():
                shutil.copy2(nguon, goi / 'images' / nguon.name)
            anh.append({'id': it['id'], 'tep': 'images/' + nguon.name,
                        'moc_thay_the': it['source_url'],
                        'alt': it['alt'], 'title': it['title'], 'caption': it['caption'],
                        'width': it['width'], 'height': it['height']})

        (goi / 'noi-dung.html').write_text(html_body, encoding='utf-8')

        ke_hoach = {
            'huong_dan': 'Chay lan luot. Moi buoc la mot ability novamira.',
            'slug': article['slug'],
            'chong_trung': 'Truoc buoc 3 phai kiem slug chua ton tai tren WordPress.',
            'buoc': [
                {'thu_tu': 1, 'ability': 'novamira/create-upload-link + execute-php',
                 'viec': 'Tai tung tep trong images/ vao Media Library bang '
                         'wp_insert_attachment + wp_generate_attachment_metadata. '
                         'Dat alt/title/caption dung theo bang anh. Ghi lai media_id va source_url.'},
                {'thu_tu': 2, 'ability': '(thay chuoi)',
                 'viec': 'Trong noi-dung.html thay moi moc_thay_the bang source_url that. '
                         'Sau buoc nay khong duoc con chuoi @@ANH: nao.'},
                {'thu_tu': 3, 'ability': 'novamira/create-post',
                 'tham_so': {'post_type': 'post', 'post_status': 'draft',
                             'post_title': article['seo'].get('title') or topic['title'],
                             'post_name': article['slug'],
                             'post_excerpt': article['seo'].get('meta_description', '')}},
                {'thu_tu': 4, 'ability': 'novamira/rank-math-edit-post-seo',
                 'tham_so': {'seo_title': article['seo'].get('title'),
                             'meta_description': article['seo'].get('meta_description'),
                             'focus_keywords': [topic['primary_keyword']]}},
                {'thu_tu': 5, 'ability': 'novamira/update-post',
                 'viec': 'Gan chuyen muc va the, dat anh dau tien lam featured image.',
                 'tham_so': {'chuyen_muc': topic['category'], 'the': topic.get('tags', [])}},
                {'thu_tu': 6, 'ability': '(kiem lai)',
                 'viec': 'Doc lai bai vua tao: post_status phai la draft, moi <img> phai tro '
                         'wp-content/uploads, khong con @@ANH:, va JSON-LD FAQPage con nguyen.'},
            ],
            'anh': anh,
            # Duong ho-so buoc phai QA TRUOC luc thay URL anh — tac nhan moi biet
            # media_id sau khi tai len. Nen phan QA khong phu duoc phai thanh mot
            # danh sach kiem RO RANG sau khi dang. Khong co no thi buoc thay chuoi
            # nam ngoai moi cong.
            'kiem_sau_dang': [
                'post_status phai la draft',
                'post_content KHONG con chuoi @@ANH:',
                'moi <img src> phai tro wp-content/uploads',
                'so the <figure class="ficool-article-image"> phai bang %d' % len(anh),
                'JSON-LD FAQPage phai con nguyen trong post_content',
                'slug phai dung la %s' % article['slug'],
                'featured image phai la %s' % (anh[0]['id'] if anh else '(khong co anh)'),
            ],
        }
        (goi / 'ke-hoach.json').write_text(
            json.dumps(ke_hoach, ensure_ascii=False, indent=2), encoding='utf-8')

        return {'duong': self.ten, 'post_id': None, 'status': 'cho_tac_nhan',
                'link': None, 'goi': str(goi), 'media': uploaded}


def chon_cong_bo(che_do: str, thu_muc):
    """`auto`: thử theo thứ tự giàu -> nghèo -> bàn giao."""
    if che_do == 'ho-so':
        return CongBoHoSo(thu_muc)
    if che_do == 'rest':
        return CongBoRest()
    if che_do == 'novamira':
        return CongBoNovamira()
    if che_do != 'auto':
        raise ValueError('che_do khong hop le: %s' % che_do)

    nova = CongBoNovamira()
    if nova.san_sang():
        return nova
    rest = CongBoRest()
    if rest.san_sang():
        return rest
    return CongBoHoSo(thu_muc)
