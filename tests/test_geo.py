from __future__ import annotations
import json
import re
import pytest

from pipeline.bai_mau import bai_mau
from pipeline.geo import TYPE_RANK_MATH_GIU, do_geo, dung_schema, tach_buoc, tach_faq

TU_KHOA = 'máy lạnh chảy nước trong nhà'
BAI = bai_mau(TU_KHOA)
URL = 'https://ficool.top/may-lanh-chay-nuoc-trong-nha/'
TOPIC = {'id': 'ML-01', 'title': TU_KHOA, 'primary_keyword': TU_KHOA, 'content_type': 'how_to'}
ART = {'slug': 'may-lanh-chay-nuoc-trong-nha',
       'seo': {'title': 'Máy lạnh chảy nước: cách xử lý', 'meta_description': 'x'}}


def _html(bai=BAI, schema=None):
    h = '<h1>t</h1><ul><li>a</li></ul>'
    return h + (schema['json_ld'] if schema and schema['json_ld'] else '')


# ── bóc tách ────────────────────────────────────────────────────────────────
def test_tach_dung_so_cap_faq_va_buoc():
    assert len(tach_faq(BAI)) == 4
    assert len(tach_buoc(BAI)) == 4


def test_khong_lay_h3_ngoai_muc_faq():
    ngoai = '## Phần khác\n\n### Đây không phải câu hỏi FAQ?\n\nNội dung dài hơn bốn mươi ký tự để không bị lọc.\n'
    assert tach_faq(ngoai) == []


# ── schema ──────────────────────────────────────────────────────────────────
def test_sinh_faqpage_va_howto():
    s = dung_schema(TOPIC, ART, BAI, URL)
    assert s['types'] == ['FAQPage', 'HowTo']
    d = json.loads(re.search(r'>(.*)</script>', s['json_ld'], re.S).group(1))
    assert d['@context'] == 'https://schema.org'
    faq = next(n for n in d['@graph'] if n['@type'] == 'FAQPage')
    assert len(faq['mainEntity']) == 4
    assert all(q['@type'] == 'Question' and q['acceptedAnswer']['@type'] == 'Answer'
               for q in faq['mainEntity'])
    assert faq['inLanguage'] == 'vi-VN'   # site thật đang phát en-US, không lặp lại lỗi đó


def test_khong_bao_gio_phat_type_cua_rank_math():
    """Rank Math đã phát BlogPosting/WebPage/Organization/... trên ficool.top.
    Phát lại là tự tạo mâu thuẫn."""
    s = dung_schema(TOPIC, ART, BAI, URL)
    assert not (set(s['types']) & TYPE_RANK_MATH_GIU)


def test_khong_du_faq_thi_khong_phat_schema():
    it = BAI.split('## Câu hỏi thường gặp')[0] + '## Câu hỏi thường gặp (FAQ)\n\n### Một câu?\n\n' + 'x' * 60
    types = dung_schema(TOPIC, ART, it, URL)['types']
    assert 'FAQPage' not in types, 'mot cap FAQ ma van phat FAQPage'


def test_howto_chi_phat_khi_dung_loai_bai():
    khac = {**TOPIC, 'content_type': 'guide'}
    assert dung_schema(khac, ART, BAI, URL)['types'] == ['FAQPage']


# ── phép đo GEO: mỗi phép phải có khả năng đỏ ───────────────────────────────
def test_bai_mau_dat_moi_phep_geo():
    s = dung_schema(TOPIC, ART, BAI, URL)
    kq = do_geo(TOPIC, ART, BAI, _html(schema=s), s)
    assert all(kq.values()), [k for k, v in kq.items() if not v]


@pytest.mark.parametrize('phep,be_bai,be_html', [
    ('tra_loi_som',              lambda b: b.replace(f'{TU_KHOA.capitalize()} thường bắt nguồn', 'Điều này thường bắt nguồn'), None),
    ('cau_du_ngan',              lambda b: b + chr(10)*2 + (('nước ' * 45) + '. ') * 400, None),
    ('tieu_de_dang_cau_hoi',     lambda b: (b.replace('## Vì sao hiện tượng này xảy ra?', '## Nguyên nhân')
                                              .replace('## Cách kiểm tra tại nhà thế nào?', '## Các bước tại nhà')
                                              .replace('## Khi nào nên gọi kỹ thuật viên?', '## Gọi kỹ thuật viên')
                                              .split('## Câu hỏi thường gặp')[0]), None),
    ('faq_du_cap',               lambda b: b.split('## Câu hỏi thường gặp')[0], None),
    ('thuc_the_ro_rang',         lambda b: b.replace('Ficool', 'Bên mình'), None),
    ('co_dinh_dang_trich_duoc',  None, lambda h: '<h1>t</h1>'),
])
def test_be_tung_phep_geo_thi_phai_do(phep, be_bai, be_html):
    bai = be_bai(BAI) if be_bai else BAI
    s = dung_schema(TOPIC, ART, bai, URL)
    html = be_html(_html(schema=s)) if be_html else _html(schema=s)
    kq = do_geo(TOPIC, ART, bai, html, s)
    assert kq[phep] is False, f'be {phep} ma van xanh'


def test_faq_khong_tu_chua_thi_do():
    xau = BAI.replace('Hiện tượng này hiếm khi tự hết',
                      'Như trên đã nói thì nó hiếm khi tự hết')
    s = dung_schema(TOPIC, ART, xau, URL)
    assert do_geo(TOPIC, ART, xau, _html(schema=s), s)['faq_tu_chua'] is False


def test_khong_co_schema_thi_do():
    trong = {'json_ld': '', 'types': [], 'faq': 0, 'buoc': 0}
    kq = do_geo(TOPIC, ART, BAI, _html(), trong)
    assert kq['co_schema'] is False


# ── lỗi thật gặp lúc chạy bài ML-01 đầu tiên (09/09) ────────────────────────
def test_moc_nam_trong_dap_an_FAQ_khong_duoc_lot_vao_schema():
    """Mốc `<!-- INTERNAL: ... -->` đặt trong mục FAQ bị tach_faq() nuốt vào đáp
    án, rồi dung_schema() nhet nguyen van vao acceptedAnswer.text. Hai hau qua:
    may tra loi trich ra mot dap an co rac cu phap, va cong
    `khong_con_chu_thich_tho` do vi JSON-LD nam trong html_body."""
    bai = BAI.replace(
        'Chi phí thay đổi theo công suất máy',
        'Xem <!-- INTERNAL: bảng giá | /bang-gia/ --> để rõ. Chi phí thay đổi theo công suất máy')
    s = dung_schema(TOPIC, ART, bai, URL)

    assert '<!-- INTERNAL' not in s['json_ld']
    assert '<!--' not in s['json_ld']

    d = json.loads(re.search(r'>(.*)</script>', s['json_ld'], re.S).group(1))
    faq = next(n for n in d['@graph'] if n['@type'] == 'FAQPage')
    dap = [q['acceptedAnswer']['text'] for q in faq['mainEntity']]
    assert any('bảng giá để rõ' in a for a in dap), 'phai giu chu neo, chi bo cu phap'


def test_moc_anh_trong_buoc_huong_dan_cung_duoc_go():
    bai = BAI.replace('2. Mở mặt nạ dàn lạnh',
                      '2. <!-- IMAGE: IMG-009 --> Mở mặt nạ dàn lạnh')
    assert all('<!--' not in b for b in tach_buoc(bai))
