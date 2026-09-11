"""Dựng lại bài có ẢNH THẬT đã tồn tại sẵn trong Media Library.

VÌ SAO CẦN RIÊNG SCRIPT NÀY:

`dung_lai_bai.py` dựng mọi bài bằng trình giữ chỗ, vì đó là đường đi của 107 bài
còn lại. Nhưng ML-02 (post 383) đã có bốn ảnh thật sinh từ 09/09, và kế hoạch đã
chốt GIỮ NGUYÊN chúng. Chạy `dung_lai_bai.py` cho nó là thay bốn tấm ảnh thật
bằng bốn cái hộp "CẦN ẢNH" — tức là đi lùi.

NÓ KHÔNG TỰ DỰNG HTML. `assembly._the_figure()` đã có sẵn nhánh ảnh thật; điều
kiện rẽ nhánh là bản ghi `uploaded` có `source_url` và không có `giu_cho`
(assembly.py:147). Nên việc của script này chỉ là ĐẮP dữ liệu ảnh thật vào
`uploaded` rồi để pipeline làm phần còn lại. Nhờ vậy bài dựng ở đây và bài dựng
qua pipeline không thể lệch nhau vì lý do định dạng.

Alt/caption vẫn đi qua `ap_mo_ta()` như mọi bài khác, nên ảnh thật cũng được
hưởng bản sửa A131 — alt lấy từ mô tả trong mốc, không lấy từ khuôn vai trò.

Chạy:  python scripts/dung_lai_anh_co_san.py [MA...]   (bỏ trống = mọi mã trong
       config/anh-co-san.yaml)
Ra:    output/goi-dang/<MA>.html  +  một dòng QA mỗi bài
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from connectors.wordpress.publishers import CongBoHoSo          # noqa: E402
from pipeline import anh_muon, dau_vao                          # noqa: E402
from pipeline.assembly import AssemblyPipeline, doc_mo_ta       # noqa: E402
from pipeline.geo import do_geo, dung_schema                    # noqa: E402
from pipeline.images import ImagePipeline, ap_mo_ta             # noqa: E402
from pipeline.qa import QAPipeline                              # noqa: E402
from pipeline.topic_selector import TopicSelector               # noqa: E402

GOI = ROOT / 'output/goi-dang'
CAU_HINH = ROOT / 'config/anh-co-san.yaml'
GOC_SITE = 'https://ficool.top'


def doc_cau_hinh():
    return yaml.safe_load(CAU_HINH.read_text(encoding='utf-8')) or {}


def dap_anh_that(uploaded, than):
    """Thay bản ghi giữ chỗ bằng bản ghi ảnh thật, theo đúng hợp đồng của
    `assembly._the_figure`: có `source_url`, có `media_id`, KHÔNG có `giu_cho`."""
    ra = []
    for u in uploaded:
        that = than.get(u['id'])
        if not that:
            ra.append(u)
            continue
        ra.append({**u,
                   'giu_cho': False,
                   'media_id': that['id'],
                   'source_url': that['url']})
    return ra


def dung_mot(ma, ts, tam, cau_hinh):
    topic = ts.by_id(ma)
    research = dau_vao.doc_nghien_cuu(topic)
    article = dau_vao.doc_bai_viet(topic)

    images = anh_muon.gan_vao(ImagePipeline().giu_cho(topic), topic)
    mo_ta = doc_mo_ta(article['body'])
    images = [ap_mo_ta({**i, 'mo_ta': mo_ta[i['id']]}) if mo_ta.get(i['id']) else i
              for i in images]

    than = cau_hinh[ma].get('than', {})
    # Kích thước thật của tệp phải đi vào `width`/`height` của thẻ img, nếu không
    # trình duyệt tính sai tỉ lệ khung và trang bị nhảy layout khi ảnh tải xong.
    images = [{**i, 'width': than[i['id']]['width'], 'height': than[i['id']]['height']}
              if i['id'] in than else i
              for i in images]

    cb = CongBoHoSo(tam / ma)
    uploaded = dap_anh_that(cb.tai_anh(images), than)
    html = AssemblyPipeline().run(article, images, uploaded, tam / ma)

    url = '%s/%s/' % (GOC_SITE, article['slug'])
    schema = dung_schema(topic, article, article['body'], url)
    if schema['json_ld']:
        html += chr(10) + schema['json_ld']
    geo = do_geo(topic, article, article['body'], html, schema)
    qa = QAPipeline().run(topic, article, html, images, research, geo=geo)
    return html, qa


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cau_hinh = doc_cau_hinh()
    ds = argv or sorted(cau_hinh)
    la = [m for m in ds if m not in cau_hinh]
    if la:
        print('khong co trong config/anh-co-san.yaml: %s' % ', '.join(la))
        return 1

    ts = TopicSelector()
    GOI.mkdir(parents=True, exist_ok=True)

    hong = 0
    with tempfile.TemporaryDirectory() as t:
        tam = Path(t)
        for ma in ds:
            html, qa = dung_mot(ma, ts, tam, cau_hinh)
            if qa['status'] != 'PASS':
                hong += 1
                print('%-7s QA CHAN %s' % (ma, qa['blockers']))
                continue
            (GOI / (ma + '.html')).write_text(html, encoding='utf-8')
            print('%-7s ok  QA %3d/100 · %d anh that · %d khoi giu cho · %d byte'
                  % (ma, qa['overall'], html.count('wp-image-'),
                     html.count('data-anh-id'), len(html)))

    print()
    print('%d/%d bai dung lai duoc' % (len(ds) - hong, len(ds)))
    return 1 if hong else 0


if __name__ == '__main__':
    raise SystemExit(main())
