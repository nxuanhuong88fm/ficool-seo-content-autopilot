from __future__ import annotations
import os,requests
class SerperError(RuntimeError): pass
class SerperClient:
    def __init__(self,api_key=None,timeout=30):
        self.api_key=api_key or os.getenv('SERPER_API_KEY',''); self.timeout=timeout
        if not self.api_key: raise SerperError('SERPER_API_KEY is required')
    def search(self,query,num_results=None,country=None,language=None):
        payload={'q':query,'num':num_results or int(os.getenv('SERP_NUM_RESULTS','10')),'gl':country or os.getenv('SERP_COUNTRY','vn'),'hl':language or os.getenv('SERP_LANGUAGE','vi')}
        r=requests.post('https://google.serper.dev/search',headers={'X-API-KEY':self.api_key,'Content-Type':'application/json'},json=payload,timeout=self.timeout)
        if not r.ok: raise SerperError(f'SERP {r.status_code}: {r.text[:500]}')
        return r.json()
    def compact(self,query):
        return [{'position':i,'title':x.get('title',''),'url':x.get('link',''),'snippet':x.get('snippet',''),'date':x.get('date')} for i,x in enumerate(self.search(query).get('organic',[]),1)]
