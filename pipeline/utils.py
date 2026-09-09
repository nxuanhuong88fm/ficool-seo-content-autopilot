from __future__ import annotations
import re, unicodedata
from pathlib import Path
import yaml

def slugify(value):
    value=unicodedata.normalize('NFKD',value.lower().strip()).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+','-',value).strip('-')

def dump_yaml(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False),encoding='utf-8')

def load_yaml(path): return yaml.safe_load(Path(path).read_text(encoding='utf-8'))


def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp. 'máy lạnh' -> 'may lanh'.

    Cần cho tín hiệu GSC: một phần đáng kể truy vấn tiếng Việt được gõ KHÔNG DẤU,
    và so khớp thẳng thì những dòng đó cho 0 điểm — tức là vứt tín hiệu thật.
    đ/Đ không phân rã được bằng NFKD nên phải thay tay.
    """
    s = s.casefold().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')
