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
