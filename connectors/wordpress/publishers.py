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
# Mốc thứ hai, cho id attachment. Cùng khuôn với MOC_ANH để tác nhân thay cả
# hai trong một lượt, và để assembly chỉ có MỘT đường mã cho cả ba đường công bố.
MOC_MEDIA_ID = '@@MEDIA_ID:{id}@@'


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
            # Giữ chỗ thì KHÔNG có tệp để tải. Ảnh đại diện mượn đã có `media_id`
            # sẵn (attachment 390–421 của 16 ảnh trang), cũng không cần tải.
            if it.get('giu_cho'):
                # `media_id` luôn có mặt kể cả khi là None: sổ manifest đọc khoá
                # này của MỌI ảnh, thiếu một cái là KeyError giữa lượt chạy thật.
                ra.append({**it, 'source_url': '', 'media_id': it.get('media_id')})
                continue
            wp = self.client.upload_media(it['local_path'], title=it['title'], alt_text=it['alt'],
                                          caption=it['caption'], description=it['caption'])
            ra.append({**it, 'media_id': wp['id'],
                       'source_url': wp.get('source_url') or wp.get('guid', {}).get('rendered', '')})
        return ra

    def don_anh(self, uploaded):
        for it in uploaded:
            # ⚠️ KHÔNG XOÁ ẢNH MƯỢN. `media_id` của nó là attachment của trang
            # dịch vụ đang chạy trên site — xoá một bài bị QA chặn mà kéo theo
            # ảnh hero của /dich-vu/sua-chua-tu-lanh/ là hỏng thứ không liên quan.
            # Cũng không xoá giữ chỗ: nó chưa từng được tải lên.
            if it.get('giu_cho') or it.get('anh_muon') or not it.get('media_id'):
                continue
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
        # Giữ chỗ thì KHÔNG có mốc: không có tệp nào để tải, nên không có gì để
        # tác nhân thay. Ảnh đại diện mượn đã mang sẵn `media_id`.
        ra = []
        for i in images:
            if i.get('giu_cho'):
                ra.append({**i, 'source_url': '',
                           'media_id': i.get('media_id')})
                continue
            ra.append({**i, 'media_id': None,
                       'source_url': MOC_ANH.format(id=i['id']),
                       'media_id_moc': MOC_MEDIA_ID.format(id=i['id'])})
        return ra

    def don_anh(self, uploaded):
        goi = self.goc / 'goi-dang'
        if goi.exists():
            shutil.rmtree(goi)

    def dang_ban_nhap(self, topic, article, html_body, uploaded):
        goi = self.goc / 'goi-dang'
        (goi / 'images').mkdir(parents=True, exist_ok=True)

        anh = []
        for it in uploaded:
            # Giu cho thi khong co tep, khong co moc, va khong co kich thuoc that
            # — kich thuoc chi biet duoc khi anh ton tai.
            if it.get('giu_cho'):
                anh.append({'id': it['id'], 'tep': None, 'giu_cho': True,
                            'vai_tro': it.get('type'),
                            'mo_ta': it.get('mo_ta') or it.get('canh'),
                            'alt': it['alt'], 'title': it.get('title'),
                            'caption': it.get('caption'),
                            'ti_le': '%s:%s' % (it.get('ti_le_rong', 16),
                                                it.get('ti_le_cao', 9)),
                            'media_id': it.get('media_id'),
                            'anh_muon': it.get('anh_muon', False),
                            'anh_muon_nguon': it.get('anh_muon_nguon')})
                continue
            nguon = Path(it['local_path'])
            if nguon.exists():
                shutil.copy2(nguon, goi / 'images' / nguon.name)
            anh.append({'id': it['id'], 'tep': 'images/' + nguon.name,
                        # KE HOACH phai noi ro anh nay di vao O NAO. Anh
                        # `featured` khong co moc trong post_content, nen hau
                        # kiem doi `moc_thay_the` cua no nam trong HTML la doi
                        # mot thu khong bao gio co.
                        'vai_tro': it.get('type'),
                        'o': 'anh dai dien (khong o trong bai)'
                             if it.get('type') == 'featured' else 'than bai',
                        'moc_thay_the': it['source_url'],
                        'moc_media_id': it.get('media_id_moc'),
                        'bien_the': it.get('bien_the', []),
                        'alt': it['alt'], 'title': it['title'], 'caption': it['caption'],
                        'width': it['width'], 'height': it['height']})

        (goi / 'noi-dung.html').write_text(html_body, encoding='utf-8')

        # Bai co the di mot trong hai duong anh, va KE HOACH phai noi dung
        # duong dang di. Mot ban ke hoach bao "tai tung tep trong images/" khi
        # thu muc do rong la mot ban ke hoach sai.
        giu_cho = [u for u in uploaded if u.get('giu_cho')]
        anh_that = [u for u in uploaded if not u.get('giu_cho')]
        muon = [u for u in uploaded if u.get('anh_muon')]
        # Anh `featured` di vao O ANH DAI DIEN cua WordPress, khong vao
        # post_content — template #268 da render no thanh hero. Moi phep dem
        # figure/khoi giu cho trong THAN BAI phai tru no ra, neu khong thi hau
        # kiem doi 4 trong khi thuc te co 3 va bao hong mot bai dung.
        trong_than = [u for u in uploaded if u.get('type') != 'featured']
        gc_than = [u for u in giu_cho if u.get('type') != 'featured']

        if giu_cho:
            buoc_0 = {
                'thu_tu': 0, 'ability': '(NGUOI DOC — bat buoc)',
                'viec': 'DOC TUNG MO TA giu cho: %d khoi trong noi-dung.html, cong 1 DE BAI '
                        'cho anh dai dien (IMG-001, khong nam trong than bai). '
                        'Xac nhan mo ta ta DUNG thu muc do can:' % len(gc_than),
                'phai_xac_nhan': [
                    'mo ta bam dung noi dung cua muc no dung canh, khong chung chung',
                    'mo ta ta duoc mot canh CHUP DUOC, khong phai mot y tuong',
                    'alt trong data-alt doc len nghe tu nhien, khong nhoi tu khoa',
                    'anh dai dien MUON co dung danh muc thiet bi cua bai',
                ],
                'vi_sao': 'Anh chua ton tai nen khong co gi de nhin. Thu duy nhat kiem duoc '
                          'luc nay la MO TA — va mo ta sai thi nguoi chup sau se chup sai.',
                'giu_cho': [{'id': u['id'], 'vai_tro': u.get('type'),
                             'o': 'anh dai dien (khong o trong bai)'
                                  if u.get('type') == 'featured' else 'than bai',
                             'mo_ta': u.get('mo_ta') or u.get('canh'),
                             'alt': u.get('alt')} for u in giu_cho],
            }
        else:
            buoc_0 = {
                'thu_tu': 0, 'ability': '(NGUOI XEM — bat buoc)',
                'viec': 'MO TUNG TEP trong images/ ra NHIN. Bon dieu phai xac nhan bang MAT:',
                'phai_xac_nhan': [
                    'ky thuat vien la NAM',
                    'dong phuc dung mau da chon (ao lien quan)',
                    'chu doc duoc DUY NHAT la "Ficool" tren nguc ao, va chu do khong meo',
                    'KHONG co ten hang hay logo ben thu ba tren thiet bi hay dong phuc',
                ],
                'vi_sao': 'Do tren luot sinh dau tien: 3/4 anh mang nhan hieu ben thu ba du '
                          'prompt da cam. Phat hien logo, gioi tinh hay chu meo deu can THI GIAC '
                          '— khong co phep kiem tu dong nao thay duoc buoc nay. Xem RULES A117.'}

        ke_hoach = {
            'huong_dan': 'Chay lan luot. Moi buoc la mot ability novamira.',
            'slug': article['slug'],
            'duong_anh': 'giu-cho' if giu_cho else 'anh-that',
            'chong_trung': 'Truoc buoc 3 phai kiem slug chua ton tai tren WordPress.',
            'buoc': [
                buoc_0,
                {'thu_tu': 1,
                 'ability': '(BO QUA)' if giu_cho else 'novamira/create-upload-link + execute-php',
                 'viec': ('Khong co tep anh nao de tai — bai nay di duong GIU CHO. '
                          'Anh dai dien muon tu 16 anh trang da co san trong Media '
                          'Library, khong can tai gi them.') if giu_cho else
                         'Tai tung tep trong images/ vao Media Library bang '
                         'wp_insert_attachment + wp_generate_attachment_metadata. '
                         'Dat alt/title/caption dung theo bang anh. Ghi lai media_id va source_url.'},
                {'thu_tu': 2,
                 'ability': '(BO QUA)' if giu_cho else '(thay chuoi)',
                 'viec': ('Khong co moc nao de thay: khoi giu cho da la HTML hoan '
                          'chinh. Khi co anh that, thay ca khoi <figure '
                          'ficool-anh-giu-cho> bang <figure ficool-article-image> '
                          'mang <img> that — data-alt giu san alt de khoi nghi lai.'
                          ) if giu_cho else
                         'Trong noi-dung.html thay CA HAI loai moc: moc_thay_the -> source_url '
                         'that, va moc_media_id -> id attachment. Sau buoc nay khong duoc con '
                         'chuoi @@ANH: hay @@MEDIA_ID: nao. Class wp-image-<id> la thu QUYET DINH '
                         'WordPress co chen srcset hay khong — thieu no thi dien thoai cot 350px '
                         'van tai nguyen file 1376px.'},
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
                 'viec': ('Gan chuyen muc va the. Anh dai dien la ANH MUON, media_id=%d '
                          '(%s) — dat lam featured va dat rank_math_facebook_image = '
                          'media_id=%d. DAY LA ANH TAM: thay bang anh rieng khi co.'
                          % (muon[0]['media_id'], muon[0].get('anh_muon_nguon', ''),
                             muon[0].get('og_media_id') or muon[0]['media_id'])
                          ) if muon else
                         'Gan chuyen muc va the, dat anh dau tien lam featured image.',
                 'tham_so': {'chuyen_muc': topic['category'], 'the': topic.get('tags', []),
                             **({'featured_media': muon[0]['media_id'],
                                 'rank_math_facebook_image_id': muon[0].get('og_media_id')}
                                if muon else {})}},
                # CTA cot phai LAY THEO BAI. Template #268 doc ba khoa postmeta
                # nay qua the dong `{ficool_cta_*}` (ficool-child/inc/post-cta.php).
                # Khong ghi thi bai roi ve duong lui, tuc cau CTA cua BAI MAU
                # trong ban ve ("May van nhay den?") — sai voi 3 trong 4 dong
                # thiet bi. Ba gia tri deu la chu CUA KHACH trong ban do funnel.
                {'thu_tu': 5.5, 'ability': 'novamira/execute-php (update_post_meta)',
                 'viec': 'Ghi 3 khoa postmeta cho CTA cot phai. Bo qua la bai mang '
                         'CTA cua bai mau trong ban ve.',
                 'tham_so': {
                     'ficool_cta_tieu_de': topic.get('diem_chuyen_doi') or '',
                     'ficool_cta_mo_ta': topic.get('cta_chinh') or '',
                     'ficool_cta_link': topic.get('trang_dich_vu') or '/lien-he/',
                 }},
                {'thu_tu': 6, 'ability': '(kiem lai)',
                 'viec': 'Doc lai bai vua tao: post_status phai la draft, moi <img> phai tro '
                         'wp-content/uploads, khong con @@ANH:, va JSON-LD FAQPage con nguyen.'},
            ],
            'anh': anh,
            # Duong ho-so buoc phai QA TRUOC luc thay URL anh — tac nhan moi biet
            # media_id sau khi tai len. Nen phan QA khong phu duoc phai thanh mot
            # danh sach kiem RO RANG sau khi dang. Khong co no thi buoc thay chuoi
            # nam ngoai moi cong.
            'kiem_sau_dang': ([
                # ⚠️ Bai con giu cho thi KHONG duoc publish: khoi "CAN ANH" se
                # hien nguyen tren trang cong khai. Day la chot chan.
                'post_status phai la draft chung nao post_content con data-anh-id',
                'so khoi giu cho (data-anh-id) phai bang %d' % len(gc_than),
                'moi khoi giu cho phai co data-alt khong rong',
                'post_content KHONG duoc chua data-anh-id="IMG-001" — o anh dai '
                'dien do template #268 render, khong nam trong than bai',
                'featured image phai la anh muon media_id=%s' % (
                    muon[0]['media_id'] if muon else '(khong co)'),
                'JSON-LD FAQPage phai con nguyen trong post_content',
                'slug phai dung la %s' % article['slug'],
                'so the <figure class="ficool-article-image"> phai bang %d' % len(trong_than),
            ] if giu_cho else [
                'post_status phai la draft',
                'post_content KHONG con chuoi @@ANH:',
                'moi <img src> phai tro wp-content/uploads',
                'so the <figure class="ficool-article-image"> phai bang %d' % len(trong_than),
                'JSON-LD FAQPage phai con nguyen trong post_content',
                'slug phai dung la %s' % article['slug'],
                'featured image phai la IMG-001, va IMG-001 KHONG duoc xuat hien '
                'trong post_content — template #268 da render o do roi',
                'post_content KHONG con chuoi @@MEDIA_ID:',
                'moi <img> phai co class="wp-image-<so>" — thieu la WordPress khong chen srcset',
                'sau apply_filters(the_content) phai THAY srcset tren ca %d anh' % len(trong_than),
                'anh og (1200x630) da gan vao truong anh social cua Rank Math',
            ]),
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
