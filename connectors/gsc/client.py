from __future__ import annotations
import os, json
from datetime import date, timedelta
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
SCOPES=['https://www.googleapis.com/auth/webmasters.readonly']; BASE='https://www.googleapis.com/webmasters/v3/sites'
class GSCError(RuntimeError): pass
class GSCClient:
    def __init__(self,site_url=None,credentials_path=None,timeout=30):
        self.site_url=site_url or os.getenv('GSC_SITE_URL',''); self.timeout=timeout
        if not self.site_url: raise GSCError('GSC_SITE_URL is required')
        raw=os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON','')
        if raw:
            try: info=json.loads(raw)
            except json.JSONDecodeError as e: raise GSCError('GOOGLE_APPLICATION_CREDENTIALS_JSON is invalid JSON') from e
            self.credentials=service_account.Credentials.from_service_account_info(info,scopes=SCOPES)
        else:
            path=credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS','')
            if not path: raise GSCError('GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS_JSON is required')
            self.credentials=service_account.Credentials.from_service_account_file(path,scopes=SCOPES)
    def _token(self):
        if not self.credentials.valid: self.credentials.refresh(Request())
        return self.credentials.token
    def query(self,start_date,end_date,dimensions=None,row_limit=25000,start_row=0,filters=None):
        site=requests.utils.quote(self.site_url,safe=''); payload={'startDate':start_date,'endDate':end_date,'dimensions':dimensions or ['query','page'],'rowLimit':row_limit,'startRow':start_row}
        if filters: payload['dimensionFilterGroups']=[{'groupType':'and','filters':filters}]
        r=requests.post(f'{BASE}/{site}/searchAnalytics/query',headers={'Authorization':f'Bearer {self._token()}'},json=payload,timeout=self.timeout)
        if not r.ok: raise GSCError(f'GSC {r.status_code}: {r.text[:500]}')
        dims=payload['dimensions']; rows=[]
        for row in r.json().get('rows',[]):
            item={d:(row.get('keys',[])[i] if i<len(row.get('keys',[])) else None) for i,d in enumerate(dims)}
            item.update({k:row.get(k) for k in ('clicks','impressions','ctr','position')}); rows.append(item)
        return rows
    def last_n_days(self,n=90,dimensions=None):
        end=date.today()-timedelta(days=2); start=end-timedelta(days=n-1); return self.query(start.isoformat(),end.isoformat(),dimensions=dimensions)
