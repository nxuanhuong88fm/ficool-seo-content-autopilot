from __future__ import annotations
import os, uuid
from pathlib import Path

from pipeline.topic_selector import TopicSelector
from pipeline.research import ResearchPipeline
from pipeline.article import ArticlePipeline
from pipeline.images import ImagePipeline, ap_mo_ta
from pipeline.assembly import AssemblyPipeline, doc_mo_ta
from pipeline.geo import dung_schema, do_geo
from pipeline.qa import QAPipeline
from connectors.wordpress.publishers import chon_cong_bo
from pipeline import anh_muon, dau_vao, manifest
from pipeline.utils import dump_yaml

KHOA_WP = ('WP_URL', 'WP_USERNAME', 'WP_APPLICATION_PASSWORD')
GOC_SITE = os.getenv('WP_URL', 'https://ficool.top').rstrip('/')


def _ghep_va_cham(topic, article, images, uploaded, research, root):
    """Ghép HTML -> gắn JSON-LD -> đo GEO -> chấm QA.

    JSON-LD phải nằm trong html_body TRƯỚC khi QA chấm, để cổng soi đúng cái
    sẽ được đăng."""
    html_body = AssemblyPipeline().run(article, images, uploaded, root)
    url = f"{GOC_SITE}/{article['slug']}/"
    schema = dung_schema(topic, article, article['body'], url)
    if schema['json_ld']:
        html_body += chr(10) + schema['json_ld']
    geo = do_geo(topic, article, article['body'], html_body, schema)
    qa = QAPipeline().run(topic, article, html_body, images, research, geo=geo)
    qa['schema'] = {'types': schema['types'], 'faq': schema['faq'], 'buoc': schema['buoc']}
    dump_yaml(root / 'qa.yaml', qa)
    (root / 'article.html').write_text(html_body, encoding='utf-8')
    return html_body, qa


class DaLamRoi(RuntimeError):
    pass


class QAChan(RuntimeError):
    pass


def run_topic(topic_id, output_root=None, use_mock_images=False,
              bo_qua_chong_trung=False, dang_bai='ho-so',
              nghien_cuu='gemini', viet='gemini', thu_muc_dau_vao=None,
              anh='giu-cho'):
    """dang_bai   : ho-so | novamira | rest | auto  (connectors/wordpress/publishers.py)
    nghien_cuu : gemini | toi     — `toi` bo Gemini research + Serper + GSC
    viet       : gemini | toi     — `toi` bo Gemini text
    anh        : giu-cho | gemini — MAC DINH `giu-cho`: khong goi API, dung
                 trinh giu cho tai dung vi tri can anh. `gemini` phai khai ro.
    """
    if anh not in ('giu-cho', 'gemini'):
        raise ValueError('anh phai la giu-cho hoac gemini, nhan %r' % anh)
    topic = TopicSelector().by_id(topic_id)

    if not bo_qua_chong_trung and topic_id in manifest.da_lam():
        raise DaLamRoi(f'{topic_id} da co ban nhap truoc do — xem output/manifests/')

    run_id = f'{topic_id}-{uuid.uuid4().hex[:8]}'
    root = Path(output_root or os.getenv('FICOOL_OUTPUT_DIR', 'output/runs')) / run_id
    root.mkdir(parents=True, exist_ok=True)

    cong_bo = chon_cong_bo(dang_bai, root)
    if cong_bo.can_khoa and not cong_bo.san_sang():
        raise RuntimeError(
            f"duong '{cong_bo.ten}' can WP_URL/WP_USERNAME/WP_APPLICATION_PASSWORD. "
            "Dung --dang-bai=ho-so de chay khong can khoa.")

    # Chỉ DỰNG thứ thực sự dùng: ResearchPipeline.__init__ tạo GSCClient +
    # SerperClient + Gemini ngay lúc khởi tạo, nên `nghien_cuu='toi'` mà vẫn
    # dựng nó là vẫn đòi đủ ba khoá.
    if nghien_cuu == 'toi':
        research = dau_vao.doc_nghien_cuu(topic, thu_muc_dau_vao)
    else:
        research = ResearchPipeline().run(topic, root)
    dump_yaml(root / 'research.yaml', research)

    if viet == 'toi':
        article = dau_vao.doc_bai_viet(topic, thu_muc_dau_vao)
        dump_yaml(root / 'article-draft.yaml',
                  {'topic': topic, 'article': article['body'], 'seo': article['seo']})
        (root / 'article.md').write_text(article['body'], encoding='utf-8')
    else:
        article = ArticlePipeline().run(topic, research, root)

    if use_mock_images:
        from connectors.image_provider import MockImageProvider
        provider, images = MockImageProvider(), []
        for i in range(1, 5):
            a = provider.generate(prompt=topic['title'], output_path=root / 'images' / f'img-{i:03d}',
                                  width=1600, height=900)
            images.append({'id': f'IMG-{i:03d}', 'width': a.width, 'height': a.height,
                           'alt': topic['title'], 'title': topic['title'], 'caption': topic['title'],
                           'filename': a.path.name, 'local_path': str(a.path)})
    elif anh == 'giu-cho':
        # Khong goi API lan nao. Anh dai dien MUON tu 16 anh trang da co san.
        images = anh_muon.gan_vao(ImagePipeline().giu_cho(topic), topic)
    else:
        images = ImagePipeline().generate(topic, article['body'], root)
        for i in images:
            i['local_path'] = str(root / 'images' / i['filename'])

    # Mo ta trong moc phai den ca HAI noi: HTML (nguoi doc bai thay) va
    # ke-hoach.json (nguoi dien anh doc o buoc 0). Gan o day, truoc ca hai.
    # `ap_mo_ta` doi luon alt/title/caption theo mo ta — khuon vai tro chi con la
    # duong lui. Goi o day nen ca ke-hoach.json lan HTML deu mang cung mot alt.
    mo_ta = doc_mo_ta(article['body'])
    images = [ap_mo_ta({**i, 'mo_ta': mo_ta[i['id']]}) if mo_ta.get(i['id']) else i
              for i in images]

    # (1) tai/dat cho anh TRUOC  (2) ghep HTML bang URL that  (3) QA dung bai se dang  (4) moi dang
    uploaded = cong_bo.tai_anh(images)
    html_body, qa = _ghep_va_cham(topic, article, images, uploaded, research, root)

    if qa['status'] != 'PASS':
        cong_bo.don_anh(uploaded)
        raise QAChan(f'QA BLOCK {qa["blockers"]} — chi tiet: {qa["chi_tiet"]}')

    wp = cong_bo.dang_ban_nhap(topic, article, html_body, uploaded)
    dump_yaml(root / 'wordpress.yaml', wp)
    manifest.ghi(run_id, topic, article, qa, wp)
    return root, qa, wp
