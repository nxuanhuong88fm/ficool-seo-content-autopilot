"""Dựng lại post_content của bài ĐÃ ĐĂNG, không đụng vào sổ.

Vì sao cần một script riêng thay vì chạy lại `ficool run --force`: `run_topic`
ghi một bản ghi manifest MỚI cho mỗi lượt. Chạy lại 60 bài là sinh 60 bản ghi
không có `wp_post_id`, và từ đó `cho-dang` báo 60 gói đang chờ trong khi thực tế
không gói nào chờ. Sổ là thứ chống trùng dựa vào — làm nhiễu nó đắt hơn nhiều so
với việc viết script này.

Nó dùng ĐÚNG các hàm mà `run_topic` dùng (`dau_vao`, `ImagePipeline.giu_cho`,
`anh_muon.gan_vao`, `ap_mo_ta`, `AssemblyPipeline`, `QAPipeline`), nên bài dựng
lại ở đây và bài dựng qua pipeline không thể lệch nhau vì lý do khác.

Chạy:  python scripts/dung_lai_bai.py [MA...]     (bỏ trống = mọi tệp dau-vao/)
Ra:    output/goi-dang/<MA>.html  +  một dòng QA mỗi bài
"""
from __future__ import annotations

import sys
from pathlib import Path

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
GOC_SITE = 'https://ficool.top'


def dung_mot(ma: str, ts: TopicSelector, tam: Path):
    topic = ts.by_id(ma)
    research = dau_vao.doc_nghien_cuu(topic)
    article = dau_vao.doc_bai_viet(topic)

    images = anh_muon.gan_vao(ImagePipeline().giu_cho(topic), topic)
    mo_ta = doc_mo_ta(article['body'])
    images = [ap_mo_ta({**i, 'mo_ta': mo_ta[i['id']]}) if mo_ta.get(i['id']) else i
              for i in images]

    cb = CongBoHoSo(tam / ma)
    uploaded = cb.tai_anh(images)
    html = AssemblyPipeline().run(article, images, uploaded, tam / ma)

    url = '%s/%s/' % (GOC_SITE, article['slug'])
    schema = dung_schema(topic, article, article['body'], url)
    if schema['json_ld']:
        html += chr(10) + schema['json_ld']
    geo = do_geo(topic, article, article['body'], html, schema)
    qa = QAPipeline().run(topic, article, html, images, research, geo=geo)
    return html, qa, images


def main(argv=None):
    import tempfile

    argv = list(sys.argv[1:] if argv is None else argv)
    ts = TopicSelector()
    ds = argv or sorted(p.stem for p in (ROOT / 'dau-vao').glob('*.yaml'))
    GOI.mkdir(parents=True, exist_ok=True)

    hong = 0
    with tempfile.TemporaryDirectory() as t:
        tam = Path(t)
        for ma in ds:
            html, qa, images = dung_mot(ma, ts, tam)
            if qa['status'] != 'PASS':
                hong += 1
                print('%-7s QA CHAN %s' % (ma, qa['blockers']))
                continue
            (GOI / (ma + '.html')).write_text(html, encoding='utf-8')
            print('%-7s ok  QA %3d/100 · %d khoi giu cho · %d byte'
                  % (ma, qa['overall'], html.count('data-anh-id'), len(html)))

    print()
    print('%d/%d bai dung lai duoc' % (len(ds) - hong, len(ds)))
    return 1 if hong else 0


if __name__ == '__main__':
    raise SystemExit(main())
