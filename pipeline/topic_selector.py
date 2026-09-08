from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVICE={'ML':'may-lanh','MG':'may-giat','TL':'tu-lanh','TD':'tu-mat-tu-dong','MN':'may-nuoc-nong','TK':'thiet-bi-khac'}
CATEGORY={'ML':'Máy lạnh','MG':'Máy giặt','TL':'Tủ lạnh','TD':'Tủ mát/Tủ đông','MN':'Máy nước nóng','TK':'Thiết bị khác'}

def _derive_tag(title):
    s=title.casefold()
    if any(x in s for x in ['vệ sinh','làm sạch']): return 'vệ sinh'
    if any(x in s for x in ['bảo trì','bảo dưỡng','thanh magie','chống giật','checklist kiểm tra']): return 'bảo trì'
    if any(x in s for x in ['lắp ','lắp đặt','vị trí đặt','kê chân']): return 'lắp đặt'
    if any(x in s for x in ['chi phí','nên chọn','khác nhau','khi nào nên','nhiệt độ','sắp xếp']): return 'kinh nghiệm hay'
    return 'lỗi thường gặp'

def _derive_intent(tag): return 'commercial' if tag in ('vệ sinh','bảo trì','lắp đặt') else 'informational'
def _derive_funnel(tag): return {'lỗi thường gặp':'problem_aware','kinh nghiệm hay':'solution_aware'}.get(tag,'service_aware')

class TopicSelector:
    def __init__(self):
        seed=json.loads((ROOT/'knowledge/seo/topic-seed.json').read_text(encoding='utf-8'))
        self.topics=[]
        for prefix,titles in seed.items():
            for n,title in enumerate(titles,1):
                tag=_derive_tag(title)
                words=title.rstrip('?').split(':')[0].strip()
                primary=words.casefold()
                self.topics.append({'id':f'{prefix}-{n:02d}','category':CATEGORY[prefix],'title':title,'tags':[tag],'primary_keyword':primary,'secondary_keywords':[title.casefold(),f'{primary} tại TP.HCM'],'intent':_derive_intent(tag),'funnel_stage':_derive_funnel(tag),'content_type':'troubleshooting' if tag=='lỗi thường gặp' else ('how_to' if tag in ('vệ sinh','lắp đặt') else 'guide'),'pillar':CATEGORY[prefix],'related_topics':[f'{prefix}-{i:02d}' for i in range(1,19) if i!=n][:3],'service':SERVICE[prefix],'priority':'high' if tag=='lỗi thường gặp' else 'medium','status':'planned'})
        if len(self.topics)!=108: raise RuntimeError(f'Expected 108 topics, got {len(self.topics)}')
    def by_id(self,topic_id):
        for t in self.topics:
            if t['id']==topic_id: return t
        raise KeyError(topic_id)
    def all(self): return self.topics
