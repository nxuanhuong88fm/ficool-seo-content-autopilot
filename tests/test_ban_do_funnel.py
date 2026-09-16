"""Bản đồ funnel của khách — nguồn sự thật cho tiêu đề, từ khoá, CTA, liên kết.

Vì sao đáng một tệp test riêng: đây là tệp quyết định NỘI DUNG của 108 bài. Một
lỗi im lặng ở đây (slug nuốt chữ, liên kết trỏ vào hư không, tag dính liền vì
tách sai dấu) không làm chương trình đổ — nó chỉ làm 108 bài sai một cách đều
đặn, và ta chỉ biết sau khi đã đăng.

Mỗi phép dưới đây đo BẢN ĐỒ ĐÃ NHẬP, không đo lại tệp .xlsx: tệp .xlsx nằm ở kho
khác, CI không với tới.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.topic_selector import TEP_BAN_DO, TopicSelector

pytestmark = pytest.mark.skipif(not TEP_BAN_DO.exists(),
                                reason='chua nhap ban do: chay scripts/nhap_ban_do.py')


@pytest.fixture(scope='module')
def ban_do():
    return json.loads(TEP_BAN_DO.read_text(encoding='utf-8'))


# ── hình dạng ───────────────────────────────────────────────────────────────
def test_du_108_bai_va_ma_dung_khuon(ban_do):
    bai = ban_do['bai']
    assert len(bai) == 108
    assert all(re.fullmatch(r'(ML|MG|TL|TD|MN|TK)-\d{2}', b['id']) for b in bai)
    # 6 dong thiet bi x 18 bai, khong dong nao thua thieu
    from collections import Counter
    assert set(Counter(b['id'].split('-')[0] for b in bai).values()) == {18}


def test_stt_la_song_anh_voi_ma_bai(ban_do):
    """Ánh xạ `stt = chi_so_nhom*18 + n` là điều duy nhất cho phép nối bản đồ của
    khách với mã bài của kho. Nếu khách chèn/xoá một dòng thì phép này đỏ ngay."""
    for i, b in enumerate(ban_do['bai']):
        assert b['stt'] == i + 1, b['id']


def test_co_ghi_phien_ban_ban_do(ban_do):
    """Không có phiên bản thì không phân biệt được `ML-01` của bản đồ nào."""
    assert ban_do['phien_ban'].startswith('funnel-map-v2+')
    assert len(ban_do['sha256_12']) == 12


# ── slug ────────────────────────────────────────────────────────────────────
def test_108_slug_deu_khac_nhau_va_khong_rong(ban_do):
    slugs = [b['slug'] for b in ban_do['bai']]
    assert all(slugs), 'co slug rong'
    assert len(set(slugs)) == 108, 'slug trung: %d/108' % len(set(slugs))


def test_slug_khong_nuot_chu_d(ban_do):
    """`slugify` bản cũ nuốt mất chữ `đ` — 43/108 tiêu đề có chữ đó. Nếu ai lùi
    bản vá ấy, slug sẽ ngắn đi và test này đỏ."""
    ket = [b for b in ban_do['bai'] if 'đ' in b['primary_keyword'].lower()]
    assert ket, 'khong con tu khoa nao co chu d — fixture sai chu khong phai ma sai'
    for b in ket:
        so_chu = len(re.sub(r'[^a-z0-9]', '', b['slug']))
        so_goc = len(re.sub(r'[^0-9a-zA-ZÀ-ỹ]', '', b['primary_keyword']))
        assert so_chu == so_goc, '%s: slug %r ngan hon tu khoa %r' % (
            b['id'], b['slug'], b['primary_keyword'])


# ── liên kết nội bộ ─────────────────────────────────────────────────────────
def test_moi_lien_ket_noi_bo_tro_toi_bai_co_that(ban_do):
    ma = {b['id'] for b in ban_do['bai']}
    for b in ban_do['bai']:
        for x in b['internal_links']:
            assert x in ma, '%s tro toi %s khong ton tai' % (b['id'], x)


def test_khong_bai_nao_tu_lien_ket_chinh_no(ban_do):
    for b in ban_do['bai']:
        assert b['id'] not in b['internal_links'], b['id']


def test_tu_lien_ket_bi_bo_nhung_duoc_ghi_ra(ban_do):
    """11/108 ô trong bản đồ của khách trỏ bài về CHÍNH NÓ. Bộ nhập bỏ liên kết
    đó — nhưng phải ghi ra, vì đây là lỗi trong bản đồ mà chỉ khách sửa được.
    Im lặng thay bằng một bài khác do ta tự chọn là ta viết lại chiến lược."""
    bo = ban_do['tu_lien_ket_da_bo']
    assert bo, 'khong con o nao tu tro — ban do da sua thi cap nhat phep nay'
    ma = {b['id'] for b in ban_do['bai']}
    assert set(bo) <= ma


def test_khong_con_o_nao_chua_giai_duoc(ban_do):
    assert ban_do['chua_giai_duoc'] == [], ban_do['chua_giai_duoc']


def test_moi_bai_P1_co_it_nhat_mot_lien_ket(ban_do):
    """Nguyên tắc 3 của khách: "Mỗi bài P1 có 3 internal link"."""
    thieu = [b['id'] for b in ban_do['bai']
             if b['uu_tien_trien_khai'] == 'P1' and not b['internal_links']]
    assert not thieu, 'bai P1 khong co lien ket nao: %s' % thieu


def test_bai_P1_thieu_lien_ket_dung_bang_so_o_tu_tro(ban_do):
    """6 bài P1 chỉ còn MỘT liên kết, vì ô thứ hai của chúng trỏ về chính nó.
    Bản đồ của khách hụt so với nguyên tắc 3 của chính khách.

    Phép này KHÔNG đòi ta vá: nó chốt rằng phần hụt đúng bằng phần đã bỏ, để
    không ai lặng lẽ nhét một bài bất kỳ vào cho đủ số.
    """
    mot = {b['id'] for b in ban_do['bai']
           if b['uu_tien_trien_khai'] == 'P1' and len(b['internal_links']) == 1}
    assert mot <= set(ban_do['tu_lien_ket_da_bo']), (
        'co bai P1 hut lien ket vi ly do khac ngoai o tu tro: %s'
        % sorted(mot - set(ban_do['tu_lien_ket_da_bo'])))


# ── từ khoá: đây là nguồn của alt ảnh, phải sạch ────────────────────────────
def test_tu_khoa_chinh_khong_rong_va_khong_co_dau_hai_cham(ban_do):
    """`ImagePipeline.plan` lấy từ khoá chính làm chủ đề ảnh rồi ghép vào alt.
    Một dấu hai chấm ở đây sinh ra alt kiểu 'Tổng quan: a: b' trên cả 4 ảnh."""
    for b in ban_do['bai']:
        assert b['primary_keyword'].strip(), b['id']
        assert ':' in b['title'] or True          # tieu de CO the co, khong sao
        assert ':' not in b['primary_keyword'], (b['id'], b['primary_keyword'])


def test_tag_duoc_tach_roi_chu_khong_dinh_lien(ban_do):
    """Khách ngăn cách bằng xuống dòng trong ô. Quên tách `\\n` thì sinh ra
    những nhãn dính kiểu 'Kinh nghiệm hay\\nLỗi thường gặp'."""
    for b in ban_do['bai']:
        for t in b['tags']:
            assert '\n' not in t and t == t.strip(), (b['id'], repr(t))


# ── ưu tiên ─────────────────────────────────────────────────────────────────
def test_moi_bai_deu_co_muc_uu_tien(ban_do):
    for b in ban_do['bai']:
        assert b['uu_tien_trien_khai'] in ('P1', 'P2'), (b['id'], b['uu_tien_trien_khai'])


def test_dung_79_bai_P1(ban_do):
    """Con số của khách. Lệch nghĩa là nhập sai cột hoặc khách đổi bản đồ."""
    assert sum(1 for b in ban_do['bai'] if b['uu_tien_trien_khai'] == 'P1') == 79


# ── TopicSelector đọc bản đồ, không đoán nữa ────────────────────────────────
def test_selector_lay_nguon_tu_ban_do():
    ts = TopicSelector()
    assert ts.nguon == 'ban-do-funnel'
    assert ts.phien_ban_ban_do.startswith('funnel-map-v2+')


def test_mac_dinh_xep_P1_len_truoc():
    ids = [t['priority'] for t in TopicSelector().all()]
    assert ids[:79] == ['P1'] * 79
    assert ids[79:] == ['P2'] * 29


def test_thu_tu_stt_giu_nguyen_thu_tu_cua_khach():
    ts = TopicSelector(thu_tu='stt')
    assert [t['stt'] for t in ts.all()] == list(range(1, 109))


def test_thu_tu_la_thi_chan():
    with pytest.raises(ValueError, match='thu_tu'):
        TopicSelector(thu_tu='linh-tinh')


def test_selector_mang_theo_phan_chien_luoc():
    """Nếu chỉ mang tiêu đề sang thì việc nhập bản đồ là vô nghĩa."""
    t = TopicSelector().by_id('ML-01')
    assert t['cta_chinh'] and t['funnel_stage'] == 'F1'
    assert t['trang_thai_khach'] and t['loi_hua']
    assert t['related_topics'] and all(x != 'ML-01' for x in t['related_topics'])


def test_ma_bai_da_doi_nghia_so_voi_hat_giong_cu():
    """Đây là cái bẫy im lặng, viết thành phép đo để nó không im nữa:
    `ML-01` cũ là "chảy nước", `ML-01` của bản đồ v2 là "không lạnh"."""
    moi = TopicSelector().by_id('ML-01')['title'].casefold()
    assert 'không lạnh' in moi
    cu = json.loads((Path(TEP_BAN_DO).parent / 'topic-seed.json')
                    .read_text(encoding='utf-8'))['ML'][0].casefold()
    assert 'chảy nước' in cu
    assert moi != cu


# ── trang dịch vụ: chỉ URL CÓ THẬT ──────────────────────────────────────────
def test_trang_dich_vu_deu_la_duong_dan_dich_vu_that(ban_do):
    """Không bịa URL. 15 trang dịch vụ đọc thẳng từ ficool.top; chặng nào khách
    chưa có trang thì để TRỐNG chứ không trỏ bừa sang trang khác."""
    for b in ban_do['bai']:
        u = b['trang_dich_vu']
        assert u == '' or re.fullmatch(r'/dich-vu/[a-z0-9-]+/', u), (b['id'], u)


def test_bai_thieu_trang_dich_vu_duoc_ghi_ra_chu_khong_lap_im(ban_do):
    """41 bài trỏ tới dịch vụ khách chưa có trang. Đó là việc phải báo, không
    phải việc lặng lẽ vá bằng một URL gần đúng."""
    thieu = {x[0] for x in ban_do['thieu_trang_dich_vu']}
    khong_co = {b['id'] for b in ban_do['bai'] if not b['trang_dich_vu']}
    assert thieu == khong_co
