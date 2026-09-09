from __future__ import annotations
from collections import defaultdict

from pipeline.utils import bo_dau

def prioritize_topics(topics,gsc_rows):
    metrics=defaultdict(lambda:{'clicks':0.0,'impressions':0.0,'position':100.0})
    for row in gsc_rows:
        q=bo_dau(row.get('query') or '')
        for t in topics:
            phrases=[t['primary_keyword'],*t.get('secondary_keywords',[])]
            if any(bo_dau(p) in q or q in bo_dau(p) for p in phrases if p):
                m=metrics[t['id']]; m['clicks']+=float(row.get('clicks') or 0); m['impressions']+=float(row.get('impressions') or 0); m['position']=min(m['position'],float(row.get('position') or 100))
    out=[]
    for t in topics:
        m=metrics[t['id']]
        opportunity=min(m['impressions'],10000)*max(0,(20-m['position'])/20)+m['clicks']*3
        score=round(opportunity+min(m['impressions']/100,50)+(20 if t['funnel_stage'] in ('service_aware','ready_to_buy') else 10),2)
        out.append({**t,'gsc_signal':m,'gsc_priority_score':score})
    return sorted(out,key=lambda x:(-x['gsc_priority_score'],x['id']))
