"""CLI thật cho ficool — đúng những lệnh README mô tả.

Bản cũ (scripts/ficool.py) chỉ đăng ký duy nhất `demo`, nên `topics`, `show` và
`run` trong README đều báo "invalid choice".
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _in(*a):
    print(*a, flush=True)


def _ep_utf8():
    """Console Windows mặc định cp1252; in tiếng Việt là UnicodeEncodeError.
    Trên CI (ubuntu) không lộ, nên lỗi này chỉ đau ở máy người dùng."""
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass


def cmd_topics(args):
    from pipeline.topic_selector import TopicSelector
    ds = TopicSelector().all()
    if args.category:
        ds = [t for t in ds if t['id'].startswith(args.category.upper())]
    for t in ds:
        _in(f"{t['id']}  {t['funnel_stage']:<14} {t['category']:<14} {t['title']}")
    _in(f'\n{len(ds)} chủ đề.')


def cmd_show(args):
    from pipeline.topic_selector import TopicSelector
    _in(json.dumps(TopicSelector().by_id(args.topic_id), ensure_ascii=False, indent=2))


def cmd_run(args):
    from pipeline.run import run_topic, DaLamRoi, QAChan

    topic_id = args.topic_id
    if args.auto:
        from pipeline.chon import chon_tiep_theo, HetChuDe
        try:
            topic, _ = chon_tiep_theo()
        except HetChuDe as e:
            _in(f'HẾT CHỦ ĐỀ: {e}'); return 0
        topic_id = topic['id']
        _in(f'Tự chọn: {topic_id} — {topic["title"]} (điểm GSC {topic["gsc_priority_score"]})')
    elif not topic_id:
        _in('Cần <topic_id> hoặc --auto'); return 2

    args.topic_id = topic_id
    try:
        root, qa, wp = run_topic(args.topic_id, output_root=args.output_dir,
                                 use_mock_images=args.mock_images,
                                 bo_qua_chong_trung=args.force)
    except DaLamRoi as e:
        _in(f'BỎ QUA: {e}'); return 0
    except QAChan as e:
        _in(f'QA CHẶN: {e}'); return 2
    _in(f'Thư mục : {root}')
    _in(f'QA      : {qa["status"]} ({qa["overall"]}/100)')
    _in(f'WordPress: {wp.get("status")} {wp.get("link") or ""}')
    return 0


def cmd_demo(args):
    """Chạy khô: không mạng, không khoá. Dùng ĐÚNG bộ dựng và ĐÚNG cổng QA của
    production, nên demo hỏng nghĩa là production hỏng."""
    from connectors.image_provider import MockImageProvider
    from pipeline.assembly import AssemblyPipeline
    from pipeline.qa import QAPipeline
    from pipeline.utils import dump_yaml, slugify

    tu_khoa = args.keyword
    slug = slugify(tu_khoa)
    out = ROOT / 'output/demo' / slug
    out.mkdir(parents=True, exist_ok=True)

    doan = (f'{tu_khoa.capitalize()} là tình huống thường gặp với thiết bị điện lạnh '
            'trong điều kiện khí hậu TP.HCM. Trước khi tháo lắp bất cứ bộ phận nào, '
            'hãy ngắt nguồn điện và quan sát dấu hiệu bằng mắt. ')
    than = (f'# {tu_khoa.capitalize()}: nguyên nhân và cách xử lý\n\n'
            f'{tu_khoa.capitalize()} có thể đến từ nhiều nguyên nhân khác nhau.\n\n'
            '<!-- IMAGE: IMG-001 -->\n\n## Dấu hiệu thường gặp\n\n'
            + doan * 14 +
            '\n\nTham khảo <!-- INTERNAL: bảng giá dịch vụ | /bang-gia/ --> trước khi quyết định.\n\n'
            '## Khi nào nên gọi kỹ thuật viên\n\n' + doan * 14 +
            '\n\n## Câu hỏi thường gặp (FAQ)\n\nFicool phục vụ khu vực TP.HCM. Đặt lịch để được hỗ trợ.\n')

    provider, images = MockImageProvider(), []
    for i, muc_dich in enumerate(['bối cảnh chủ đề', 'nguyên nhân thường gặp',
                                  'cách kiểm tra an toàn', 'khi nào cần kỹ thuật viên'], 1):
        a = provider.generate(f'{tu_khoa}; {muc_dich}', out / 'images' / f'img-{i:03d}')
        images.append({'id': f'IMG-{i:03d}', 'width': a.width, 'height': a.height,
                       'filename': a.path.name, 'local_path': str(a.path),
                       'alt': f'{tu_khoa} — {muc_dich}', 'title': muc_dich,
                       'caption': f'Hình minh họa: {muc_dich}.',
                       # URL giả dạng WordPress: để cổng QA chạy nguyên vẹn ở
                       # chế độ demo, thay vì phải miễn trừ một phép đo.
                       'source_url': f'https://ficool.top/wp-content/uploads/demo/{a.path.name}'})

    article = {'body': than, 'slug': slug,
               'seo': {'title': f'{tu_khoa.capitalize()}: cách xử lý',
                       'meta_description': f'Nguyên nhân {tu_khoa}, cách kiểm tra an toàn '
                                           'và khi nào nên gọi kỹ thuật viên tại TP.HCM.'}}
    topic = {'id': 'DEMO', 'title': tu_khoa, 'category': 'Máy lạnh', 'tags': ['lỗi thường gặp'],
             'primary_keyword': tu_khoa}

    html_body = AssemblyPipeline().run(article, images, images, out)
    qa = QAPipeline().run(topic, article, html_body, images, {'serp': [{'link': 'https://vd.vn'}]})

    (out / 'article.md').write_text(than, encoding='utf-8')
    dump_yaml(out / 'demo.yaml', {'topic': topic, 'seo': article['seo'], 'qa': qa,
                                  'images': [i['id'] for i in images]})
    _in(f'Demo: {out.relative_to(ROOT)}')
    _in(f'QA  : {qa["status"]} ({qa["overall"]}/100)' + (f' — chặn: {qa["blockers"]}' if qa['blockers'] else ''))
    return 0 if qa['status'] == 'PASS' else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog='ficool')
    sub = p.add_subparsers(dest='command', required=True)

    s = sub.add_parser('topics', help='liệt kê 108 chủ đề')
    s.add_argument('--category', help='lọc theo tiền tố: ML, MG, TL, TD, MN, TK')
    s.set_defaults(fn=cmd_topics)

    s = sub.add_parser('show', help='xem chi tiết một chủ đề')
    s.add_argument('topic_id'); s.set_defaults(fn=cmd_show)

    s = sub.add_parser('run', help='chạy pipeline cho một chủ đề')
    s.add_argument('topic_id', nargs='?', default=None)
    s.add_argument('--auto', action='store_true',
                   help='tự chọn chủ đề ưu tiên cao nhất chưa làm (dùng cho cron)')
    s.add_argument('--mock-images', action='store_true', help='không gọi API ảnh')
    s.add_argument('--output-dir', default=None)
    s.add_argument('--force', action='store_true', help='bỏ qua chống trùng')
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser('demo', help='chạy khô, không mạng, không khoá')
    s.add_argument('keyword'); s.set_defaults(fn=cmd_demo)

    _ep_utf8()
    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == '__main__':
    sys.exit(main())
