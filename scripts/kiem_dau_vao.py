"""Kiểm tệp đầu vào TRƯỚC khi chạy pipeline.

Vì sao đáng một script riêng: mỗi lượt `ficool run` tốn thời gian dựng nghiên
cứu, ghép HTML, dựng schema rồi mới tới cổng QA. Một tiêu đề SEO dài 61 ký tự
hay một cụm bị cấm đều làm hỏng lượt đó, và ta chỉ biết ở cuối.

Lô 1 mất 4 lượt chạy để lộ 4 cụm bị cấm — mỗi lượt chỉ lộ được một. Lô 4 mất
một lượt vì tiêu đề dài đúng một ký tự. Script này gom mọi phép kiểm rẻ về
trước, và chạy hết trong một giây.

Nó KHÔNG thay cổng QA: QA đo bài đã ghép xong, còn đây chỉ đo tệp đầu vào.

Chạy:  python scripts/kiem_dau_vao.py [MA...]      (bỏ trống = kiểm hết dau-vao/)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import dau_vao  # noqa: E402
from pipeline.topic_selector import TopicSelector  # noqa: E402

TEP_CAM = ROOT / 'config/forbidden-claims.yaml'
MOC_ANH = re.compile(r'<!-- IMAGE:\s*(?P<id>[A-Za-z0-9_-]+)\s*(?:\|\s*(?P<mo_ta>[^>]*?)\s*)?-->')


def _luat_cam():
    d = yaml.safe_load(TEP_CAM.read_text(encoding='utf-8'))
    return d.get('luat', list(d.values())) if isinstance(d, dict) else d


def kiem_mot(ma: str, ts: TopicSelector) -> list:
    """Trả danh sách lỗi. Rỗng nghĩa là tệp sẵn sàng chạy."""
    loi = []
    p = ROOT / 'dau-vao' / (ma + '.yaml')
    if not p.exists():
        return ['khong co tep %s' % p.name]

    # 1. Bộ kiểm đầu vào THẬT — dùng lại đúng hàm mà pipeline sẽ gọi, nên
    #    không có chuyện script này xanh mà pipeline vẫn đỏ vì lý do khác.
    try:
        topic = ts.by_id(ma)
        dau_vao.doc_nghien_cuu(topic)
        art = dau_vao.doc_bai_viet(topic)
    except Exception as e:                                  # noqa: BLE001
        return ['%s: %s' % (type(e).__name__, str(e).replace(chr(10), ' | '))]

    than = art['body']

    # 2. Luật cấm — cổng QA cũng đo, nhưng ở đây thì rẻ hơn nhiều lần.
    for r in _luat_cam():
        for m in re.finditer(r['mau'], than, re.I):
            loi.append('luat cam [%s]: %r' % (r['ten'], m.group(0)))

    # 3. Bốn mốc ảnh, mỗi mốc phải kèm mô tả — đây là thứ QA KHÔNG đo, vì mốc
    #    không mô tả vẫn chạy được (lùi về khuôn). Nhưng khuôn thì chung chung.
    co = {m.group('id'): (m.group('mo_ta') or '').strip() for m in MOC_ANH.finditer(than)}
    for i in range(1, 5):
        mid = 'IMG-%03d' % i
        if mid not in co:
            loi.append('thieu moc %s' % mid)
        elif not co[mid]:
            loi.append('%s khong co mo ta — se lui ve khuon chung chung' % mid)

    return loi


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ts = TopicSelector()
    ma_list = argv or sorted(p.stem for p in (ROOT / 'dau-vao').glob('*.yaml'))
    if not ma_list:
        print('dau-vao/ rong')
        return 0

    hong = 0
    for ma in ma_list:
        loi = kiem_mot(ma, ts)
        if loi:
            hong += 1
            print('%-7s HONG' % ma)
            for x in loi:
                print('          %s' % x)
        else:
            print('%-7s ok' % ma)

    print()
    print('%d/%d tep san sang' % (len(ma_list) - hong, len(ma_list)))
    return 1 if hong else 0


if __name__ == '__main__':
    raise SystemExit(main())
