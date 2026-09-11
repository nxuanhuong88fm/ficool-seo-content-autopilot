"""Trình giữ chỗ ảnh — đường mặc định từ 10/09/2026.

Sinh ảnh cho 107 bài tốn $28,68, vượt mức khách chi được. Nên bài viết trước, ảnh
điền sau: mỗi chỗ cần ảnh có một khối GIỮ CHỖ nhìn thấy được, mang mô tả bám ngữ
cảnh mục đó, cộng alt đã tính sẵn.

Khác `test_dong_phuc.py` ở một điểm quan trọng: các phép ở đây đo HÀNH VI THẬT,
không đo chuỗi trong prompt. Không có ảnh nào được sinh ra thì cũng không có gì
phải tin vào lời hứa của model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from connectors.wordpress.publishers import CongBoHoSo
from pipeline import anh_muon
from pipeline.assembly import MOC_ANH, AssemblyPipeline, _the_giu_cho, doc_mo_ta
from pipeline.images import ImagePipeline
from pipeline.topic_selector import TopicSelector

TOPIC = TopicSelector().by_id('ML-01')


def _ke_hoach():
    return ImagePipeline().giu_cho(TOPIC)


# ── mốc mang mô tả ──────────────────────────────────────────────────────────
def test_moc_tach_dung_ma_va_mo_ta():
    m = MOC_ANH.search('<!-- IMAGE: IMG-002 | Cận cảnh máng hứng nước tràn -->')
    assert m.group('id') == 'IMG-002'
    assert m.group('mo_ta') == 'Cận cảnh máng hứng nước tràn'


def test_moc_CU_khong_mo_ta_van_doc_duoc():
    """Bài đã viết theo mốc cũ không được hỏng chỉ vì hợp đồng mốc mở rộng."""
    m = MOC_ANH.search('<!-- IMAGE: IMG-002 -->')
    assert m.group('id') == 'IMG-002'
    assert m.group('mo_ta') is None


def test_mo_ta_trong_moc_di_duoc_vao_khoi_giu_cho(tmp_path):
    # Dung IMG-002/IMG-003: IMG-001 mang vai tro `featured`, no di vao O ANH DAI
    # DIEN chu khong vao than bai, nen khong dung de do khoi giu cho duoc.
    than = ('# T\n\n<!-- IMAGE: IMG-002 | Kỹ thuật viên đo dòng điện tại dàn nóng -->'
            '\n\n<!-- IMAGE: IMG-003 -->')
    imgs = _ke_hoach()[1:3]
    h = AssemblyPipeline().run({'body': than}, imgs, imgs, tmp_path)

    assert 'Kỹ thuật viên đo dòng điện tại dàn nóng' in h
    # IMG-003 khong co mo ta rieng -> lui ve khuon `canh` cua vai tro
    assert imgs[1]['canh'] in h


def test_mo_ta_doi_luon_alt_chu_khong_chi_doi_chu_hien_ra(tmp_path):
    """`data-alt` phai theo MO TA, khong theo khuon vai tro.

    Khuon cua IMG-002 la `Cận cảnh dấu hiệu {chu_de}` — hop cho bai
    troubleshooting, vo nghia cho 31/60 bai loai guide/how_to da dang ngay
    10/09/2026: "Cận cảnh dấu hiệu lắp đặt tủ đông".

    `data-alt` sinh ra DE nguoi dien anh chep lai ma khong phai nghi lai. Alt sai
    khong nam yen trong ban nhap — no di thang vao anh that sau nay.
    """
    than = '# T\n\n<!-- IMAGE: IMG-002 | Cận cảnh phiếu báo giá đặt trên quầy -->'
    imgs = _ke_hoach()[1:2]
    h = AssemblyPipeline().run({'body': than}, imgs, imgs, tmp_path)

    assert 'data-alt="Cận cảnh phiếu báo giá đặt trên quầy – Ficool"' in h
    assert 'dấu hiệu' not in h, 'van con dinh khuon vai tro'


def test_mo_ta_co_ky_tu_HTML_thi_bi_escape():
    """Mô tả do tác nhân viết. Một dấu `<` lọt nguyên vào là vỡ thẻ figure."""
    h = _the_giu_cho({**_ke_hoach()[0], 'mo_ta': 'ống <thoát> & "máng" hứng'})
    assert '<thoát>' not in h
    assert '&lt;tho' in h and '&amp;' in h and '&quot;' in h


def test_mo_ta_di_duoc_ca_vao_ke_hoach_chu_khong_chi_vao_HTML(tmp_path):
    """Bước 0 bảo người ĐỌC TỪNG MÔ TẢ. Đưa cho họ bản khuôn trong khi bài mang
    bản theo ngữ cảnh là đưa nhầm bản — và người chụp ảnh sau sẽ chụp theo bản
    họ đọc, không theo bản nằm trong HTML."""
    than = ('# T\n\n<!-- IMAGE: IMG-001 | '
            'Kỹ thuật viên cầm remote trước dàn lạnh -->')
    assert doc_mo_ta(than) == {'IMG-001': 'Kỹ thuật viên cầm remote trước dàn lạnh'}

    imgs = [{**a, 'mo_ta': doc_mo_ta(than).get(a['id'])} if doc_mo_ta(than).get(a['id'])
            else a for a in anh_muon.gan_vao(_ke_hoach(), TOPIC)]
    cb = CongBoHoSo(tmp_path)
    kq = cb.dang_ban_nhap(
        {'category': 'c', 'tags': [], 'primary_keyword': 'k', 'title': 't'},
        {'slug': 's', 'seo': {'title': 't', 'meta_description': 'm'}}, '<h1>x</h1>',
        cb.tai_anh(imgs))
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))
    b0 = [b for b in kh['buoc'] if b['thu_tu'] == 0][0]
    m1 = [g for g in b0['giu_cho'] if g['id'] == 'IMG-001'][0]
    assert m1['mo_ta'] == 'Kỹ thuật viên cầm remote trước dàn lạnh'


# ── hình dạng khối giữ chỗ ──────────────────────────────────────────────────
def test_khoi_mang_du_bon_thuoc_tinh_data():
    h = _the_giu_cho(_ke_hoach()[1])
    for k in ('data-anh-id="IMG-002"', 'data-vai-tro="instructional"',
              'data-ti-le="16:9"', 'data-alt="'):
        assert k in h, k


def test_khoi_GIU_class_ficool_article_image():
    """Cổng QA `anh_da_chen` đếm đúng chuỗi này. Đổi tên class là làm đỏ một
    cổng vì lý do sai — cổng vẫn đúng, chỉ là ta đổi thứ nó đang đo."""
    assert 'ficool-article-image' in _the_giu_cho(_ke_hoach()[0])


def test_khoi_KHONG_co_the_img():
    """Có `<img>` là có yêu cầu mạng hỏng và một ô vỡ trên trang."""
    h = _the_giu_cho(_ke_hoach()[0])
    assert '<img' not in h and 'src=' not in h


def test_QA_anh_da_chen_van_xanh_khi_ca_bon_deu_la_giu_cho(tmp_path):
    imgs = _ke_hoach()
    than = '# T\n\n' + '\n\n'.join('<!-- IMAGE: %s -->' % a['id'] for a in imgs)
    h = AssemblyPipeline().run({'body': than}, imgs, imgs, tmp_path)

    # BA khoi, khong phai bon: IMG-001 (`featured`) di vao o anh dai dien.
    trong_than = [i for i in imgs if i.get('type') != 'featured']
    assert h.count('ficool-article-image') >= len(trong_than)
    assert h.count('data-anh-id') == 3
    assert 'IMG-001' not in h


# ── không gọi API ───────────────────────────────────────────────────────────
def test_giu_cho_KHONG_dung_toi_provider():
    """`GeminiImageProvider.__init__` gọi `tao_client()` ngay, tức đòi khoá API.
    Đường giữ chỗ chạm tới provider là bắt cả đường không dùng API phải có khoá."""
    class _No:
        def __getattr__(self, ten):
            raise AssertionError('duong giu-cho da cham vao provider: .%s' % ten)

    assert len(ImagePipeline(provider=_No()).giu_cho(TOPIC)) == 4


def test_run_topic_chan_gia_tri_anh_la():
    from pipeline.run import run_topic
    with pytest.raises(ValueError, match='anh phai la'):
        run_topic('ML-01', anh='linh-tinh')


# ── ảnh mượn ────────────────────────────────────────────────────────────────
def test_ca_108_bai_deu_giai_ra_mot_anh_muon():
    """Trả None cho 41 bài là để chúng không có ảnh đại diện mà không ai biết."""
    for t in TopicSelector().all():
        m = anh_muon.chon(t)
        assert m['anh'] and m['og'], t['id']


def test_bai_co_trang_dich_vu_lay_dung_anh_cua_trang_do():
    t = TopicSelector().by_id('ML-01')
    assert t['trang_dich_vu'] == '/dich-vu/sua-chua-may-lanh/'
    bang = anh_muon.cau_hinh()['theo_trang_dich_vu']['/dich-vu/sua-chua-may-lanh/']
    assert anh_muon.chon(t)['anh'] == bang['anh']


def test_danh_muc_khong_co_trang_dich_vu_thi_ve_hero_trang_chu():
    """TK — 18 bài, và site không có trang dịch vụ nào cho nhóm này (§33.5)."""
    m = anh_muon.chon(TopicSelector().by_id('TK-01'))
    assert m['anh'] == anh_muon.cau_hinh()['hero_trang_chu']['anh']
    assert 'hero' in m['nguon']


def test_chi_vai_tro_featured_duoc_gan_anh_muon():
    ra = anh_muon.gan_vao(_ke_hoach(), TOPIC)
    muon = [x for x in ra if x.get('anh_muon')]
    assert len(muon) == 1 and muon[0]['type'] == 'featured'
    assert all(not x.get('media_id') for x in ra if x['type'] != 'featured')


# ── đường công bố ───────────────────────────────────────────────────────────
def test_tai_anh_KHONG_sinh_moc_cho_giu_cho(tmp_path):
    """Mốc `@@ANH:` là lời hứa "sẽ có URL thay vào đây". Không có tệp nào để tải
    thì lời hứa đó không ai giữ được, và mốc sẽ nằm nguyên trong bài đã đăng."""
    up = CongBoHoSo(tmp_path).tai_anh(anh_muon.gan_vao(_ke_hoach(), TOPIC))
    assert all(u['source_url'] == '' for u in up)
    assert all('@@ANH:' not in str(u.get('source_url')) for u in up)
    assert all('media_id' in u for u in up), 'so manifest doc khoa nay cua MOI anh'


def test_don_anh_KHONG_xoa_anh_muon():
    """`media_id` của ảnh mượn là attachment của trang dịch vụ đang chạy. Một bài
    bị QA chặn mà kéo theo ảnh hero của /dich-vu/sua-chua-tu-lanh/ là hỏng thứ
    không liên quan."""
    from connectors.wordpress.publishers import CongBoRest

    da_xoa = []

    class _Client:
        def delete_media(self, mid):
            da_xoa.append(mid)

    cb = CongBoRest.__new__(CongBoRest)
    cb.client = _Client()
    cb.don_anh(anh_muon.gan_vao(_ke_hoach(), TOPIC))
    assert da_xoa == []


def test_ke_hoach_giu_cho_mang_chot_chan_publish(tmp_path):
    imgs = anh_muon.gan_vao(_ke_hoach(), TOPIC)
    cb = CongBoHoSo(tmp_path)
    up = cb.tai_anh(imgs)
    kq = cb.dang_ban_nhap(
        {'category': 'c', 'tags': [], 'primary_keyword': 'k', 'title': 't'},
        {'slug': 's', 'seo': {'title': 't', 'meta_description': 'm'}}, '<h1>x</h1>', up)
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))

    assert kh['duong_anh'] == 'giu-cho'
    ds = ' | '.join(kh['kiem_sau_dang'])
    assert 'data-anh-id' in ds, 'thieu chot chan: bai con giu cho van publish duoc'
    assert 'draft' in ds
    # buoc 0 phai doi noi dung: khong con anh de "xem"
    b0 = [b for b in kh['buoc'] if b['thu_tu'] == 0][0]
    assert 'DOC' in b0['ability'] or 'DOC' in b0['viec']
    assert len(b0['giu_cho']) == 4


def test_ke_hoach_anh_that_van_giu_nguyen_khang_dinh_srcset(tmp_path):
    """Nới cho đường giữ chỗ mà nới luôn đường ảnh thật là mất phép đo đã có."""
    imgs = [{**a, 'local_path': 'x.webp', 'filename': 'x.webp', 'title': 't',
             'width': 1376, 'height': 768}
            for a in ImagePipeline().plan(TOPIC)]
    cb = CongBoHoSo(tmp_path)
    kq = cb.dang_ban_nhap(
        {'category': 'c', 'tags': [], 'primary_keyword': 'k', 'title': 't'},
        {'slug': 's', 'seo': {'title': 't', 'meta_description': 'm'}}, '<h1>x</h1>',
        cb.tai_anh(imgs))
    kh = json.loads((Path(kq['goi']) / 'ke-hoach.json').read_text(encoding='utf-8'))

    assert kh['duong_anh'] == 'anh-that'
    ds = ' | '.join(kh['kiem_sau_dang'])
    assert 'srcset' in ds and 'wp-image' in ds


# ── CSS: chỉ token đã duyệt, và selector phải nhân đôi ──────────────────────
TEP_CSS = Path(r'D:\ClaudeCoding\Ficool website\ficool-child\assets\css\components.css')


@pytest.mark.skipif(not TEP_CSS.exists(), reason='kho site khong co o may nay')
def test_css_giu_cho_dung_selector_nhan_doi_va_token_da_duyet():
    """Bricks sinh luật theo ID cho bố cục; luật một class thua. Cả tệp này dùng
    lối `.input.input` / `.btn.btn` — luật mới phải theo."""
    css = TEP_CSS.read_text(encoding='utf-8')
    i = css.find('.ficool-anh-giu-cho')
    assert i != -1, 'chua them kieu cho khoi giu cho'
    doan = css[i:i + 1200]
    assert '.ficool-anh-giu-cho.ficool-anh-giu-cho' in doan
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', doan), 'de ma mau tho, phai dung token'


# ── tầng 0: chỉ đích danh theo mã bài (11/09) ───────────────────────────────
#
# Tầng 2 định tuyến theo TIỀN TỐ mã bài, mà tiền tố là DÒNG thiết bị chứ không
# phải THIẾT BỊ. Nên 18 bài TD đều về ảnh tủ mát và 18 bài MN đều về ảnh bình
# chứa, để hai ảnh 416 và 418 nằm ở 0 lượt dùng (RULES A126).
def test_theo_bai_doi_duoc_anh_ma_ban_do_funnel_chi_sai_thiet_bi():
    """TD-01 ("tủ đông không đông đá") được bản đồ funnel xếp vào trang tủ MÁT,
    nên tầng 1 cho nó ảnh tủ mát. Đây là chỗ tầng 0 phải thắng."""
    t = TopicSelector().by_id('TD-01')
    assert t['trang_dich_vu'] == '/dich-vu/sua-chua-tu-mat/'
    bang = anh_muon.cau_hinh()['theo_trang_dich_vu']
    m = anh_muon.chon(t)
    assert m['anh'] == bang['/dich-vu/sua-chua-tu-dong/']['anh']
    assert m['anh'] != bang['/dich-vu/sua-chua-tu-mat/']['anh']
    assert m['nguon'].startswith('theo_bai')


def test_theo_bai_thang_ca_tang_trang_dich_vu():
    """Bẻ đỏ bằng cách đặt tầng 0 SAU tầng 1: ML-14 có `trang_dich_vu` trong bản
    đồ nên tầng 1 sẽ nuốt mất nó."""
    t = TopicSelector().by_id('ML-14')
    assert (t.get('trang_dich_vu') or '').strip(), 'ML-14 phai co trang_dich_vu'
    thao_do = anh_muon.cau_hinh()['theo_trang_dich_vu']['/dich-vu/thao-do-lap-dat-may-lanh/']
    assert anh_muon.chon(t)['anh'] == thao_do['anh']


def test_bai_ngoai_bang_khong_bi_dong_vao():
    t = TopicSelector().by_id('TD-08')          # tủ mát, giữ mặc định
    tu_mat = anh_muon.cau_hinh()['theo_trang_dich_vu']['/dich-vu/sua-chua-tu-mat/']
    assert anh_muon.chon(t)['anh'] == tu_mat['anh']


def test_moi_dich_trong_theo_bai_deu_co_trong_bang_anh():
    c = anh_muon.cau_hinh()
    for ma, dv in (c.get('theo_bai') or {}).items():
        assert dv in c['theo_trang_dich_vu'], '%s tro toi %s khong co trong bang' % (ma, dv)


def test_moi_ma_trong_theo_bai_deu_la_chu_de_that():
    ts = TopicSelector()
    for ma in (anh_muon.cau_hinh().get('theo_bai') or {}):
        assert ts.by_id(ma), 'theo_bai co ma la: %s' % ma


def test_khong_con_anh_trang_nao_o_0_luot_dung():
    """Phép đo đã mở ra tầng 0. Ảnh 416 (tủ đông), 418 (máy trực tiếp) và 400
    (tháo dỡ di dời) từng ở 0 lượt trong khi vẫn có bài hợp với chúng."""
    dung = {anh_muon.chon(t)['anh'] for t in TopicSelector().all()}
    moi = {v['anh'] for v in anh_muon.cau_hinh()['theo_trang_dich_vu'].values()}
    assert moi - dung == set(), 'con anh o 0 luot: %s' % sorted(moi - dung)
