"""Nhập bản đồ funnel của khách (.xlsx) thành `knowledge/seo/ban-do-funnel.json`.

Vì sao phải có bước nhập chứ không đọc thẳng .xlsx:
  1. Tệp .xlsx nằm ở KHO KHÁC (`Ficool website/108-chu-de/`). CI của kho này
     không với tới được, mà bản đồ thì quyết định tiêu đề, từ khoá, CTA và liên
     kết nội bộ của cả 108 bài — không thể để nó nằm ngoài tầm kiểm.
  2. Bản đồ có PHIÊN BẢN. `ML-01` của bản cũ là "chảy nước", của bản này là
     "không lạnh". Sổ manifest phải ghi được mình viết theo bản đồ nào, nếu
     không thì bài chưa viết sẽ bị bỏ qua còn bài đã đăng sẽ bị viết lại.

Chạy:  python scripts/nhap_ban_do.py [đường-dẫn-xlsx]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.utils import slugify  # noqa: E402

XLSX_MAC_DINH = (ROOT.parent / 'Ficool website' / '108-chu-de'
                 / '108-chu-de-dien-lanh-content-funnel-map-v2.xlsx')
RA = ROOT / 'knowledge' / 'seo' / 'ban-do-funnel.json'

# Thứ tự khối danh mục trong .xlsx trùng thứ tự tiền tố của kho — đã kiểm:
# 6 khối liên tục, mỗi khối đúng 18 dòng, không xen kẽ.
TIEN_TO = ['ML', 'MG', 'TL', 'TD', 'MN', 'TK']

SHEET_CHIEN_LUOC = '108 chủ đề - Chiến lược'
SHEET_FUNNEL = 'Content Funnel Map'


def _bang(sheet, dong_tieu_de: int):
    """Trả về list dict, khoá là tiêu đề cột."""
    rows = [[c.value for c in r] for r in sheet.iter_rows(min_row=dong_tieu_de)]
    hdr = [str(x).strip() if x is not None else '' for x in rows[0]]
    ra = []
    for r in rows[1:]:
        if r[0] in (None, ''):
            continue
        ra.append({h: (v.strip() if isinstance(v, str) else v)
                   for h, v in zip(hdr, r) if h})
    return ra


def _tang(gia_tri: str) -> str:
    """'F1 — Thu hút nhu cầu' -> 'F1'. Giữ nguyên 'Nurture'."""
    if not gia_tri:
        return ''
    return gia_tri.split('—')[0].split('-')[0].strip()


def _uu_tien(gia_tri: str) -> str:
    """'P1 — Tạo nhu cầu dịch vụ' -> 'P1'."""
    if not gia_tri:
        return ''
    return gia_tri.split('—')[0].strip()


def _tach_danh_sach(gia_tri) -> list:
    """Khách ngăn cách nhiều giá trị bằng XUỐNG DÒNG trong ô, không phải dấu phẩy.

    Bỏ sót `\\n` ở đây thì cột Tags cho ra những nhãn dính liền kiểu
    'Kinh nghiệm hay\\nLỗi thường gặp' — đếm ra 12 nhãn khác nhau thay vì 5.
    """
    if not gia_tri:
        return []
    if not isinstance(gia_tri, str):
        return [str(gia_tri)]
    ra = [gia_tri]
    for dau in ('\n', ';', '|', ','):
        ra = [p for x in ra for p in x.split(dau)]
    return [x.strip() for x in ra if x.strip()]


# ── điểm chuyển đổi đích -> trang dịch vụ thật trên ficool.top ───────────────
# 15 trang dịch vụ đang publish, đọc thẳng từ site ngày 09/09/2026. KHÔNG bịa
# URL: chặng nào khách chưa có trang dịch vụ thì để trống và ghi vào `thieu_dich_vu`.
TRANG_DICH_VU = {
    ('sua-chua', 'Máy lạnh'): '/dich-vu/sua-chua-may-lanh/',
    ('sua-chua', 'Máy giặt'): '/dich-vu/sua-chua-may-giat/',
    ('sua-chua', 'Tủ lạnh'): '/dich-vu/sua-chua-tu-lanh/',
    ('sua-chua', 'Tủ mát, tủ đông'): '/dich-vu/sua-chua-tu-mat/',
    ('sua-chua', 'Máy nước nóng'): '/dich-vu/sua-binh-nong-lanh/',
    ('ve-sinh', 'Máy lạnh'): '/dich-vu/ve-sinh-may-lanh/',
    ('ve-sinh', 'Máy giặt'): '/dich-vu/ve-sinh-may-giat/',
    ('ve-sinh', 'Tủ lạnh'): '/dich-vu/ve-sinh-tu-lanh/',
    ('bao-tri', 'Máy lạnh'): '/dich-vu/bao-tri-may-lanh/',
    ('bao-tri', 'Máy giặt'): '/dich-vu/bao-tri-may-giat/',
    ('bao-tri', 'Tủ lạnh'): '/dich-vu/bao-tri-tu-lanh/',
    ('lap-dat', 'Máy lạnh'): '/dich-vu/lap-moi-may-lanh/',
}


def _viec(diem: str) -> str:
    """'Kiểm tra / sửa chữa Máy lạnh' -> 'sua-chua'."""
    s = (diem or '').casefold()
    if 'lắp đặt' in s or 'tư vấn' in s:
        return 'lap-dat'
    if 'bảo trì' in s or 'định kỳ' in s:
        return 'bao-tri'
    if 'vệ sinh' in s:
        return 've-sinh'
    if 'sửa chữa' in s or 'kiểm tra' in s or 'dịch vụ' in s:
        return 'sua-chua'
    return ''


def nhap(duong_xlsx: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(duong_xlsx, data_only=True)
    cl = _bang(wb[SHEET_CHIEN_LUOC], 5)
    fn = _bang(wb[SHEET_FUNNEL], 4)
    if len(cl) != 108 or len(fn) != 108:
        raise SystemExit('cho 108 dong moi sheet, nhan %d va %d' % (len(cl), len(fn)))

    theo_stt = {int(r['STT']): r for r in fn}

    bai = []
    for i, r in enumerate(cl):
        stt = int(r['STT'])
        f = theo_stt[stt]
        if f['Chủ đề'] != r['Chủ đề']:
            raise SystemExit('STT %d: hai sheet ghi hai tieu de khac nhau' % stt)

        tien_to = TIEN_TO[i // 18]
        ma = '%s-%02d' % (tien_to, i % 18 + 1)
        tu_khoa = (r.get('Từ khóa chính') or '').strip()

        bai.append({
            'id': ma,
            'stt': stt,
            'category': r['Danh mục'],
            'title': r['Chủ đề'],
            'slug': slugify(tu_khoa) if tu_khoa else slugify(r['Chủ đề']),
            'primary_keyword': tu_khoa,
            'secondary_keywords': _tach_danh_sach(r.get('Từ khóa phụ')),
            'tags': _tach_danh_sach(r.get('Tags')),
            'intent': r.get('Intent') or '',
            'giai_doan_khach': r.get('Trạng thái / giai đoạn') or '',
            'uu_tien': _uu_tien(r.get('Ưu tiên') or ''),
            'cta_chinh': r.get('Đề nghị / CTA chính') or '',
            # ── từ sheet funnel ──
            'funnel_stage': _tang(f.get('Funnel stage') or ''),
            'funnel_stage_day_du': f.get('Funnel stage') or '',
            'vai_tro': f.get('Vai trò') or '',
            'trang_thai_khach': f.get('Trạng thái khách hàng') or '',
            'trigger': f.get('Điểm vào / Trigger') or '',
            'loi_hua': f.get('Lời hứa chính') or '',
            'muc_dich_chuyen_tang': f.get('Mục đích chuyển tầng') or '',
            'cta_chuyen_tang': f.get('CTA chuyển tầng') or '',
            'diem_chuyen_doi': f.get('Điểm chuyển đổi đích') or '',
            'uu_tien_trien_khai': _uu_tien(f.get('Ưu tiên triển khai') or ''),
            # giải ở lượt sau, khi đã có đủ 108 tiêu đề để tra
            '_bai_tiep': f.get('Bài tiếp theo ưu tiên') or '',
            '_link': [f.get('Internal link 1') or '', f.get('Internal link 2') or ''],
        })

    # ── giải liên kết nội bộ: tiêu đề ĐẦY ĐỦ -> mã bài ──────────────────────
    theo_tieu_de = {b['title']: b['id'] for b in bai}
    chua_giai = []
    thieu_dich_vu = []
    tu_lien_ket = []
    for b in bai:
        ids = []
        for t in b.pop('_link'):
            if not t:
                continue
            ma = theo_tieu_de.get(t)
            if ma is None:
                chua_giai.append((b['id'], t))
            elif ma == b['id']:
                # 11/108 ô trong bản đồ trỏ bài về chính nó. Một liên kết tự trỏ
                # không bao giờ hợp lệ, nên BỎ — nhưng ghi ra để khách sửa bản
                # đồ, không im lặng thay bằng một bài khác do ta tự chọn.
                tu_lien_ket.append(b['id'])
            else:
                ids.append(ma)
        b['internal_links'] = ids

        t = b.pop('_bai_tiep')
        # Vài ô trỏ sang TRANG DỊCH VỤ chứ không sang bài blog — đó là ý đồ của
        # khách, không phải giá trị hỏng.
        b['bai_tiep_theo'] = theo_tieu_de.get(t, '')
        if t and not b['bai_tiep_theo'] and not t.startswith('Trang dịch vụ'):
            chua_giai.append((b['id'], 'bai_tiep: ' + t))

        khoa = (_viec(b['diem_chuyen_doi']), b['category'])
        b['trang_dich_vu'] = TRANG_DICH_VU.get(khoa, '')
        if not b['trang_dich_vu']:
            thieu_dich_vu.append((b['id'], b['diem_chuyen_doi']))

    van = hashlib.sha256(duong_xlsx.read_bytes()).hexdigest()[:12]
    return {
        'phien_ban': 'funnel-map-v2+%s' % van,
        'nguon': duong_xlsx.name,
        'sha256_12': van,
        'nhap_ngay': date.today().isoformat(),
        'so_bai': len(bai),
        'chua_giai_duoc': chua_giai,
        'thieu_trang_dich_vu': thieu_dich_vu,
        'tu_lien_ket_da_bo': tu_lien_ket,
        'bai': bai,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    duong = Path(argv[0]) if argv else XLSX_MAC_DINH
    if not duong.exists():
        raise SystemExit('khong thay tep: %s' % duong)

    d = nhap(duong)
    RA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

    slugs = [b['slug'] for b in d['bai']]
    lk = sum(len(b['internal_links']) for b in d['bai'])
    print('%s  -> %s' % (duong.name, RA.relative_to(ROOT)))
    print('  phien ban          : %s' % d['phien_ban'])
    print('  so bai             : %d' % d['so_bai'])
    print('  slug duy nhat      : %d/%d' % (len(set(slugs)), len(slugs)))
    print('  lien ket noi bo    : %d (giai duoc)' % lk)
    print('  tu lien ket da bo  : %d  %s'
          % (len(d['tu_lien_ket_da_bo']), ' '.join(d['tu_lien_ket_da_bo'])))
    print('  chua giai duoc     : %d' % len(d['chua_giai_duoc']))
    for ma, t in d['chua_giai_duoc'][:10]:
        print('      %s -> %s' % (ma, t[:60]))
    print('  co trang dich vu   : %d/%d'
          % (sum(1 for b in d['bai'] if b['trang_dich_vu']), d['so_bai']))
    if d['thieu_trang_dich_vu']:
        import collections
        c = collections.Counter(x[1] for x in d['thieu_trang_dich_vu'])
        print('  THIEU trang dich vu (%d bai):' % len(d['thieu_trang_dich_vu']))
        for k, v in c.most_common():
            print('      %2d bai  %s' % (v, k))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
