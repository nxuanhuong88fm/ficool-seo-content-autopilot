"""CLI thật cho ficool — đúng những lệnh README mô tả.

Bản cũ (scripts/ficool.py) chỉ đăng ký duy nhất `demo`, nên `topics`, `show` và
`run` trong README đều báo "invalid choice".
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from pipeline import dau_vao

ROOT = Path(__file__).resolve().parents[1]


def _in(*a):
    print(*a, flush=True)


def _nap_env():
    """Nạp `.env` ở gốc repo.

    ⚠️ Lỗi có sẵn từ bản gốc: `.env.example` tồn tại từ commit đầu và README bảo
    `cp .env.example .env`, nhưng KHÔNG dòng nào nạp tệp đó. Người dùng điền khoá
    xong, chạy vẫn báo "GEMINI_API_KEY is required" — triệu chứng trỏ sai hoàn
    toàn vào nguyên nhân.

    `override=False`: biến môi trường THẬT luôn thắng. Trên GitHub Actions không
    có `.env` nên đây là lệnh rỗng, và một tệp `.env` sót lại cũng không đè được
    secret của workflow.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / '.env', override=False)


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
                                 dang_bai=args.dang_bai,
                                 nghien_cuu=args.nghien_cuu, viet=args.viet,
                                 thu_muc_dau_vao=args.thu_muc_dau_vao)
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

    # Dùng CHUNG bảng vai trò của production (ImagePipeline.plan) thay vì tự
    # dựng danh sách riêng. Bản cũ thiếu khoá `type` nên không ảnh nào là
    # `featured`, và demo không hề đo được hành vi eager/lazy cho LCP.
    from pipeline.images import ImagePipeline
    provider, images = MockImageProvider(), []
    ke = ImagePipeline(provider=provider).plan(
        {'title': tu_khoa, 'primary_keyword': tu_khoa, 'secondary_keywords': [tu_khoa]})
    for i, vt in enumerate(ke, 1):
        a = provider.generate('%s; %s' % (tu_khoa, vt['canh']),
                              out / 'images' / ('img-%03d' % i))
        images.append({**vt, 'width': a.width, 'height': a.height,
                       'filename': a.path.name, 'local_path': str(a.path)})

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



def cmd_lo(args):
    """Chạy một LÔ nhiều bài theo thứ tự cố định."""
    from pipeline.chon import HetChuDe, chon_lo
    from pipeline.run import DaLamRoi, QAChan, run_topic

    try:
        lo, con_lai = chon_lo(args.so_luong, args.thu_tu)
    except (HetChuDe, ValueError) as e:
        _in('KHONG CHAY DUOC: %s' % e)
        return 2

    _in('Lo %d bai (thu tu: %s) — con %d chu de chua lam:' % (len(lo), args.thu_tu, con_lai))
    for t in lo:
        _in('  %s  %s' % (t['id'], t['title']))

    phan = []
    if args.nghien_cuu == 'gemini':
        phan.append('%d luot nghien cuu (Gemini+Serper+GSC)' % len(lo))
    if args.viet == 'gemini':
        phan.append('%d luot viet + %d luot meta' % (len(lo), len(lo)))
    if not args.mock_images:
        phan.append('%d anh' % (len(lo) * 4))
    _in('')
    _in('Uoc luong goi API: ' + (' + '.join(phan) if phan else 'KHONG GOI GI (tat ca do tac nhan)'))
    if args.nghien_cuu == 'toi' or args.viet == 'toi':
        _in('Dau vao tac nhan doc tu: %s/<TOPIC_ID>.yaml'
            % (args.thu_muc_dau_vao or dau_vao.THU_MUC_MAC_DINH))
    if args.xem_truoc:
        _in('')
        _in('(--xem-truoc: chi liet ke, chua chay)')
        return 0

    xong, hong = [], []
    for i, t in enumerate(lo, 1):
        _in('')
        _in('[%d/%d] %s — %s' % (i, len(lo), t['id'], t['title']))
        try:
            root, qa, wp = run_topic(t['id'], output_root=args.output_dir,
                                     use_mock_images=args.mock_images,
                                     dang_bai=args.dang_bai,
                                     nghien_cuu=args.nghien_cuu, viet=args.viet,
                                     thu_muc_dau_vao=args.thu_muc_dau_vao)
        except DaLamRoi as e:
            _in('   BO QUA: %s' % e)
            continue
        except QAChan as e:
            _in('   QA CHAN: %s' % e)
            hong.append((t['id'], 'QA'))
            continue
        except Exception as e:                       # noqa: BLE001
            # Một bài hỏng KHÔNG được giết cả lô — chín bài kia đã tốn tiền rồi.
            _in('   HONG: %s: %s' % (type(e).__name__, e))
            hong.append((t['id'], type(e).__name__))
            continue
        xong.append((t['id'], wp))
        _in('   OK — QA %d/100 · %s' % (qa['overall'], wp.get('goi') or wp.get('link') or wp['status']))

    _in('')
    _in('═' * 60)
    _in('Xong %d/%d bai.' % (len(xong), len(lo)))
    if hong:
        _in('Hong %d: %s' % (len(hong), ', '.join('%s (%s)' % h for h in hong)))
    if xong and xong[0][1].get('goi'):
        _in('')
        _in('%d goi ban giao dang cho. Bao Claude Code:' % len(xong))
        _in('   "dang %d goi dang cho len WordPress qua novamira"' % len(xong))
    return 1 if hong else 0


def cmd_cho_dang(args):
    """Liệt kê gói đã dựng nhưng chưa lên WordPress."""
    from pipeline import manifest
    ds = manifest.dang_cho()
    if not ds:
        _in('Khong co goi nao dang cho.')
        return 0
    _in('%d goi dang cho dang:' % len(ds))
    for d in ds:
        _in('  %-24s %s' % (d['run_id'], d['topic']))
        _in('      slug: %s' % d['slug'])
    return 0


def cmd_da_dang(args):
    """Đóng sổ sau khi tác nhân đã đăng."""
    from pipeline import manifest
    duong = manifest.danh_dau_da_dang(args.run_id, args.post_id, args.link or '')
    _in('Da dong so: %s -> post %s' % (duong.name, args.post_id))
    return 0



def cmd_yeu_cau(args):
    """Sinh tệp mẫu để tác nhân điền nghiên cứu và/hoặc bài viết."""
    from pipeline.chon import HetChuDe, chon_lo

    try:
        lo, con_lai = chon_lo(args.so_luong, args.thu_tu)
    except (HetChuDe, ValueError) as e:
        _in('KHONG CHAY DUOC: %s' % e)
        return 2

    thu_muc = args.thu_muc_dau_vao or dau_vao.THU_MUC_MAC_DINH
    moi, da_co = [], []
    for t in lo:
        p = dau_vao.duong_dan(t['id'], thu_muc)
        (da_co if p.exists() else moi).append(t['id'])
        dau_vao.ghi_mau(t, thu_muc, can_bai_viet=(args.viet == 'toi'))

    _in('Thu muc: %s/  (con %d chu de chua lam)' % (thu_muc, con_lai))
    if moi:
        _in('Da sinh %d mau moi: %s' % (len(moi), ', '.join(moi)))
    if da_co:
        _in('Giu nguyen %d tep da co: %s' % (len(da_co), ', '.join(da_co)))
    _in('')
    _in('Dien xong thi chay:')
    co = ' --viet=toi' if args.viet == 'toi' else ''
    _in('   python scripts/ficool.py lo %d --nghien-cuu=toi%s' % (args.so_luong, co))
    return 0



def cmd_anh_trang(args):
    """Sinh ảnh cho trang chủ và 15 trang dịch vụ (1 ảnh/trang).

    Khác lệnh `dong-phuc` ở chỗ: đây là ảnh ĐI THẲNG LÊN SITE, không phải mẫu để
    chọn. Mỗi ảnh kèm luôn bản og 1200×630 cắt ra từ chính nó — không tốn thêm
    lượt sinh nào.
    """
    import json
    from datetime import datetime

    from pipeline.anh_trang import DichSai, danh_sach, dung_prompt, sinh

    try:
        dich = danh_sach(args.ma or ())
    except DichSai as e:
        _in(str(e))
        return 2

    out = ROOT / 'output/anh-trang' / datetime.now().strftime('%Y%m%d-%H%M')
    _in('Sinh %d anh trang -> %s' % (len(dich), out.relative_to(ROOT)))
    for d in dich:
        _in('  %-26s %-8s %s' % (d['ma'], d['ti_le'], d['url']))
    _in('')
    _in('Uoc luong: %d luot sinh anh (~$%.2f o kho 1K), ban og cat lai tai may.'
        % (len(dich), 0.067 * len(dich)))
    if args.xem_truoc:
        _in('')
        _in('(--xem-truoc: chi liet ke, chua goi API)')
        if args.in_prompt:
            _in('')
            _in(dung_prompt(dich[0]))
        return 0

    from connectors.image_provider import GeminiImageProvider
    provider = GeminiImageProvider()
    out.mkdir(parents=True, exist_ok=True)
    xong, hong = [], []
    for d in dich:
        try:
            r = sinh(provider, d, out)
            xong.append(r)
            _in('  OK  %-26s %4dx%-4d %6.1f KB  og %5.1f KB'
                % (r['ma'], r['rong'], r['cao'], r['byte'] / 1024, r['byte_og'] / 1024))
        except Exception as e:                          # noqa: BLE001
            hong.append(d['ma'])
            _in('  HONG %-25s %s: %s' % (d['ma'], type(e).__name__, str(e)[:90]))

    (out / 'so.json').write_text(
        json.dumps({'sinh_luc': datetime.now().isoformat(timespec='seconds'),
                    'xong': xong, 'hong': hong}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    (out / 'DOC.md').write_text(chr(10).join([
        '# Anh trang — PHAI XEM TUNG ANH TRUOC KHI DUA LEN SITE',
        '',
        'Bon dieu kiem bang mat (khong co phep may nao thay duoc):',
        '',
        '1. Ky thuat vien la NAM.',
        '2. Dong phuc dung mau da chot (so mi tay dai + quan roi, xanh dam).',
        '3. Chi co chu "Ficool" tren nguc ao, khong meo, khong thua dau cau.',
        '4. KHONG co nhan hieu ben thu ba nao tren thiet bi hay vat dung.',
        '',
        'Them mot dieu rieng cho anh trang: anh se bi phu filter `.halftone`',
        '(grayscale .35, contrast 1.15). Xem thu anh co con doc duoc khi bac mau.',
        '',
    ] + ['- `%s` — %s (%s)' % (r['ma'], r['ten'], r['url']) for r in xong]),
        encoding='utf-8')

    _in('')
    _in('Xong %d/%d. So: %s' % (len(xong), len(dich), (out / 'so.json').relative_to(ROOT)))
    return 1 if hong else 0


def cmd_dong_phuc(args):
    """Sinh ảnh mẫu đồng phục để khách chọn.

    Mỗi phương án sinh theo từng góc chụp trong `config/dong-phuc.yaml`
    (chính diện + từ phía sau). Ảnh logo ĐÃ TÔ THEO MÀU ÁO được truyền làm ảnh
    tham chiếu — đó là cách duy nhất để model vẽ đúng cấu trúc logo thật thay vì
    bịa ra một cái na ná.
    """
    from datetime import datetime

    from pipeline.images import (CAM_NHAN_HIEU, CHU_DUOC_PHEP, NHAN_VAT, anh_logo,
                                 cau_hinh_dong_phuc, mo_ta_dong_phuc, mo_ta_logo)

    c = cau_hinh_dong_phuc()
    ten = args.phuong_an or list(c['phuong_an'])[:args.so_luong]
    la = [t for t in ten if t not in c['phuong_an']]
    if la:
        _in('Khong co phuong an: %s' % ', '.join(la))
        _in('Co san: %s' % ', '.join(c['phuong_an']))
        return 2

    goc = [g for g in c['goc_chup'] if not args.goc or g['ma'] in args.goc]
    out = ROOT / 'output/dong-phuc' / datetime.now().strftime('%Y%m%d-%H%M')

    _in('Sinh %d phuong an x %d goc = %d anh -> %s'
        % (len(ten), len(goc), len(ten) * len(goc), out.relative_to(ROOT)))
    for t in ten:
        _in('  %-24s %s' % (t, c['phuong_an'][t]['ten']))
    _in('  goc chup: %s' % ', '.join('%s (%s)' % (g['ma'], g['ten']) for g in goc))
    if args.xem_truoc:
        _in('')
        _in('(--xem-truoc: chi liet ke, chua goi API)')
        return 0

    from connectors.image_provider import GeminiImageProvider
    provider = GeminiImageProvider()
    out.mkdir(parents=True, exist_ok=True)
    xong, hong = [], []

    for t in ten:
        for g in goc:
            prompt = ' '.join([
                # KHONG dung cum 'character sheet': no moi goi model ve mot BANG MAU
                # co nhan, va lan sinh truoc no da tu them dong chu
                # "CHI SO DONG PHUC KY THUAT VIEN FICOOL (BAN CHUAN)" duoi day khung.
                'Ảnh chụp studio toàn thân một kỹ thuật viên,',
                g['canh'].strip() + ',',
                'trên nền xám trơn, không cầm thiết bị, không đạo cụ, ánh sáng studio đều.',
                'KHUNG HÌNH SẠCH: không có dòng chú thích, nhãn, tiêu đề hay thanh chữ ở'
                ' bất kỳ mép nào của khung; không watermark; không khung viền.',
                NHAN_VAT,
                mo_ta_dong_phuc(t),
                mo_ta_logo(g['logo']),
                CHU_DUOC_PHEP,
                CAM_NHAN_HIEU,
            ])
            ma = '%s--%s' % (t, g['ma'])
            try:
                a = provider.generate(prompt=prompt, output_path=out / ma,
                                      width=1024, height=1024,
                                      anh_tham_chieu=anh_logo(g['logo']))
                xong.append(ma)
                _in('  OK  %-34s %s' % (ma, a.path.name))
            except Exception as e:                      # noqa: BLE001
                hong.append(ma)
                _in('  HONG %-33s %s: %s' % (ma, type(e).__name__, str(e)[:90]))

    doc = [
        '# Phuong an dong phuc Ficool',
        '',
        'Xem tung anh, chon MOT phuong an, roi:',
        '',
        '1. Chep anh CHINH DIEN cua phuong an do vao `knowledge/brand/nhan-vat/`',
        '2. Doi `dang_dung:` trong `config/dong-phuc.yaml` sang ten phuong an',
        '',
        'Tu do no thanh anh tham chieu nhan vat cho MOI luot sinh anh bai viet.',
        '',
        'PHAI KIEM BANG MAT: chu "Ficool" co dung chinh ta khong, tagline co dung',
        '"%s" khong, logo co dung cau truc (huy hieu bo goc + chu Fi + bong tuyet)' % c['logo']['tagline'],
        'khong, va co lot nhan hieu ben thu ba nao vao khong.',
        '',
    ] + ['- `%s` — %s' % (t, c['phuong_an'][t]['ten']) for t in ten]
    (out / 'DOC.md').write_text(chr(10).join(doc), encoding='utf-8')

    _in('')
    _in('Xong %d/%d.' % (len(xong), len(xong) + len(hong)))
    if hong:
        _in('Hong: %s' % ', '.join(hong))
    return 0 if not hong else 1


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
    s.add_argument('--nghien-cuu', dest='nghien_cuu', default='gemini', choices=['gemini', 'toi'],
                   help='toi: bo Gemini research + Serper + GSC, doc tu dau-vao/<ID>.yaml')
    s.add_argument('--viet', default='gemini', choices=['gemini', 'toi'],
                   help='toi: bo Gemini text; Gemini chi con dung cho anh')
    s.add_argument('--thu-muc-dau-vao', dest='thu_muc_dau_vao', default=None)
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser('demo', help='chạy khô, không mạng, không khoá')
    s.add_argument('keyword'); s.set_defaults(fn=cmd_demo)

    _ep_utf8()
    _nap_env()
    s = sub.add_parser('lo', help='chay mot LO nhieu bai theo thu tu co dinh')
    s.add_argument('so_luong', type=int, nargs='?', default=10)
    s.add_argument('--thu-tu', dest='thu_tu', default='uu-tien', choices=['uu-tien', 'cum', 'luan-phien'],
                   help='uu-tien: P1 truoc (nguyen tac 1 cua khach, MAC DINH) · '
                        'cum: ML-01..ML-18 roi MG (gom cum chu de) · '
                        'luan-phien: vong qua 6 dong thiet bi (phu rong som)')
    s.add_argument('--dang-bai', dest='dang_bai', default='ho-so',
                   choices=['ho-so', 'novamira', 'rest', 'auto'])
    s.add_argument('--mock-images', action='store_true')
    s.add_argument('--output-dir', default=None)
    s.add_argument('--xem-truoc', dest='xem_truoc', action='store_true',
                   help='chi liet ke chu de va uoc luong goi API, chua chay')
    s.add_argument('--nghien-cuu', dest='nghien_cuu', default='gemini', choices=['gemini', 'toi'],
                   help='toi: bo Gemini research + Serper + GSC, doc tu dau-vao/<ID>.yaml')
    s.add_argument('--viet', default='gemini', choices=['gemini', 'toi'],
                   help='toi: bo Gemini text; Gemini chi con dung cho anh')
    s.add_argument('--thu-muc-dau-vao', dest='thu_muc_dau_vao', default=None)
    s.set_defaults(fn=cmd_lo)

    s = sub.add_parser('yeu-cau', help='sinh tep mau de tac nhan dien nghien cuu / bai viet')
    s.add_argument('so_luong', type=int, nargs='?', default=10)
    s.add_argument('--thu-tu', dest='thu_tu', default='uu-tien', choices=['uu-tien', 'cum', 'luan-phien'])
    s.add_argument('--viet', default='toi', choices=['gemini', 'toi'],
                   help='toi (mac dinh): mau co ca phan bai viet')
    s.add_argument('--thu-muc-dau-vao', dest='thu_muc_dau_vao', default=None)
    s.set_defaults(fn=cmd_yeu_cau)

    s = sub.add_parser('anh-trang', help='sinh anh cho trang chu + 15 trang dich vu')
    s.add_argument('--ma', nargs='*', default=None,
                   help='chi sinh cac dich nay; bo trong thi sinh het 16')
    s.add_argument('--xem-truoc', dest='xem_truoc', action='store_true')
    s.add_argument('--in-prompt', dest='in_prompt', action='store_true',
                   help='in prompt cua dich dau tien (dung voi --xem-truoc)')
    s.set_defaults(fn=cmd_anh_trang)

    s = sub.add_parser('dong-phuc', help='sinh cac phuong an dong phuc de khach chon')
    s.add_argument('--so-luong', dest='so_luong', type=int, default=4)
    s.add_argument('--phuong-an', dest='phuong_an', nargs='*', default=None,
                   help='ten phuong an cu the; bo trong thi lay --so-luong phuong an dau')
    s.add_argument('--goc', nargs='*', default=None,
                   help='chi sinh goc chup nay (truoc / sau); bo trong thi sinh het')
    s.add_argument('--xem-truoc', dest='xem_truoc', action='store_true')
    s.set_defaults(fn=cmd_dong_phuc)

    s = sub.add_parser('cho-dang', help='goi da dung nhung chua len WordPress')
    s.set_defaults(fn=cmd_cho_dang)

    s = sub.add_parser('da-dang', help='dong so sau khi tac nhan da dang')
    s.add_argument('run_id')
    s.add_argument('post_id', type=int)
    s.add_argument('--link', default=None)
    s.set_defaults(fn=cmd_da_dang)

    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == '__main__':
    sys.exit(main())
