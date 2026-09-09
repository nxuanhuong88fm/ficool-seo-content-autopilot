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
                                 bo_qua_chong_trung=args.force,
                                 dang_bai=args.dang_bai)
    except DaLamRoi as e:
        _in(f'BỎ QUA: {e}'); return 0
    except QAChan as e:
        _in(f'QA CHẶN: {e}'); return 2
    _in(f'Thư mục : {root}')
    _in(f'QA      : {qa["status"]} ({qa["overall"]}/100)')
    _in(f'WordPress: [{wp.get("duong")}] {wp.get("status")} {wp.get("link") or ""}')
    if wp.get('goi'):
        _in(f'Gói bàn giao: {wp["goi"]}')
        _in('  → bảo Claude Code: "đăng gói này lên WordPress qua novamira"')
    return 0


def cmd_demo(args):
    """Chạy khô: không mạng, không khoá. Dùng ĐÚNG bộ dựng và ĐÚNG cổng QA của
    production, nên demo hỏng nghĩa là production hỏng."""
    from connectors.image_provider import MockImageProvider
    from pipeline.run import _ghep_va_cham
    from pipeline.utils import dump_yaml, slugify

    tu_khoa = args.keyword
    slug = slugify(tu_khoa)
    out = ROOT / 'output/demo' / slug
    out.mkdir(parents=True, exist_ok=True)

    from pipeline.bai_mau import bai_mau
    than = bai_mau(tu_khoa)

    provider, images = MockImageProvider(), []
    for i, muc_dich in enumerate(['bối cảnh chủ đề', 'nguyên nhân thường gặp',
                                  'cách kiểm tra an toàn', 'khi nào cần kỹ thuật viên'], 1):
        a = provider.generate(f'{tu_khoa}; {muc_dich}', out / 'images' / f'img-{i:03d}')
        images.append({'id': f'IMG-{i:03d}', 'width': a.width, 'height': a.height,
                       'filename': a.path.name, 'local_path': str(a.path),
                       'alt': f'{tu_khoa} — {muc_dich}', 'title': muc_dich,
                       'caption': f'Hình minh họa: {muc_dich}.'})

    article = {'body': than, 'slug': slug,
               'seo': {'title': f'{tu_khoa.capitalize()}: cách xử lý',
                       'meta_description': f'Nguyên nhân {tu_khoa}, cách kiểm tra an toàn '
                                           'và khi nào nên gọi kỹ thuật viên tại TP.HCM.'}}
    topic = {'id': 'DEMO', 'title': tu_khoa, 'category': 'Máy lạnh', 'tags': ['lỗi thường gặp'],
             'content_type': 'how_to',
             'primary_keyword': tu_khoa}

    # Dùng ĐÚNG hàm ghép-và-chấm VÀ đúng thứ tự của đường ho-so thật:
    # tai_anh() trước (sinh mốc @@ANH:), rồi mới ghép — nếu không thì gói bàn
    # giao có HTML một đằng, kế hoạch một nẻo.
    from connectors.wordpress.publishers import CongBoHoSo
    cb = CongBoHoSo(out)
    da_tai = cb.tai_anh(images)
    _html, qa = _ghep_va_cham(topic, article, images, da_tai,
                              {'serp': [{'link': 'https://vd.vn'}]}, out)

    (out / 'article.md').write_text(than, encoding='utf-8')
    dump_yaml(out / 'demo.yaml', {'topic': topic, 'seo': article['seo'], 'qa': qa,
                                  'images': [i['id'] for i in images]})
    _in(f'Demo: {out.relative_to(ROOT)}')
    _in(f'QA  : {qa["status"]} ({qa["overall"]}/100)' + (f' — chặn: {qa["blockers"]}' if qa['blockers'] else ''))
    _in(f'Schema: {qa["schema"]["types"] or "(khong co)"} — {qa["schema"]["faq"]} cap FAQ, '
        f'{qa["schema"]["buoc"]} buoc')

    # Sinh luon goi ban giao. Day la cach DUY NHAT chay thu duong ho-so tu
    # dau toi cuoi ma khong ton mot dong khoa API nao — nen CI cung chay duoc.
    if qa['status'] == 'PASS':
        kq = cb.dang_ban_nhap(topic, article, _html, da_tai)
        _in('Goi ban giao: ' + str(Path(kq['goi']).relative_to(ROOT)))
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
    s.add_argument('--dang-bai', dest='dang_bai', default='ho-so',
                   choices=['ho-so', 'novamira', 'rest', 'auto'],
                   help="ho-so (mặc định): ghi gói bàn giao, KHÔNG cần khoá WordPress · "
                        "novamira/rest: máy tự đăng, cần khoá · auto: giàu→nghèo→bàn giao")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser('demo', help='chạy khô, không mạng, không khoá')
    s.add_argument('keyword'); s.set_defaults(fn=cmd_demo)

    _ep_utf8()
    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == '__main__':
    sys.exit(main())
