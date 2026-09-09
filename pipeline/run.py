from __future__ import annotations
import os, uuid
from pathlib import Path

from pipeline.topic_selector import TopicSelector
from pipeline.research import ResearchPipeline
from pipeline.article import ArticlePipeline
from pipeline.images import ImagePipeline
from pipeline.assembly import AssemblyPipeline
from pipeline.qa import QAPipeline
from pipeline.wordpress_publish import WordPressPipeline
from pipeline import manifest
from pipeline.utils import dump_yaml

KHOA_WP = ('WP_URL', 'WP_USERNAME', 'WP_APPLICATION_PASSWORD')


class DaLamRoi(RuntimeError):
    pass


class QAChan(RuntimeError):
    pass


def run_topic(topic_id, output_root=None, use_mock_images=False, bo_qua_chong_trung=False):
    topic = TopicSelector().by_id(topic_id)

    if not bo_qua_chong_trung and topic_id in manifest.da_lam():
        raise DaLamRoi(f'{topic_id} da co ban nhap truoc do — xem output/manifests/')

    run_id = f'{topic_id}-{uuid.uuid4().hex[:8]}'
    root = Path(output_root or os.getenv('FICOOL_OUTPUT_DIR', 'output/runs')) / run_id
    root.mkdir(parents=True, exist_ok=True)

    research = ResearchPipeline().run(topic, root)
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
    else:
        images = ImagePipeline().generate(topic, article['body'], root)
        for i in images:
            i['local_path'] = str(root / 'images' / i['filename'])

    co_wp = all(os.getenv(k) for k in KHOA_WP)
    if not co_wp:
        # Không có khoá: vẫn dựng và vẫn chấm QA, chỉ không đăng.
        html_body = AssemblyPipeline().run(article, images, images, root)
        qa = QAPipeline().run(topic, article, html_body, images, research)
        dump_yaml(root / 'qa.yaml', qa)
        return root, qa, {'status': 'not_run', 'reason': 'WordPress credentials missing'}

    wp_pipeline = WordPressPipeline()

    # ① tải ảnh TRƯỚC  ② dựng HTML bằng URL thật  ③ QA đúng bài sẽ đăng  ④ mới đăng
    uploaded = wp_pipeline.tai_anh(images)
    html_body = AssemblyPipeline().run(article, images, uploaded, root)

    qa = QAPipeline().run(topic, article, html_body, images, research)
    dump_yaml(root / 'qa.yaml', qa)
    if qa['status'] != 'PASS':
        wp_pipeline.don_anh(uploaded)  # bị chặn thì không để lại ảnh mồ côi
        raise QAChan(f'QA BLOCK {qa["blockers"]} — chi tiet: {qa["chi_tiet"]}')

    wp = wp_pipeline.dang_ban_nhap(topic, article, html_body, uploaded)
    dump_yaml(root / 'wordpress.yaml', wp)
    manifest.ghi(run_id, topic, article, qa, wp)
    return root, qa, wp
