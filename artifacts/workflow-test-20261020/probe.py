import requests,json,os
from pathlib import Path
BASE='https://admin.cscec.live'
OUT=Path(__file__).parent
s=requests.Session()
def call(method,path,**kw):
 r=s.request(method,BASE+'/api/'+path,timeout=60,**kw)
 try: d=r.json()
 except: raise RuntimeError(str(r.status_code)+r.text[:300])
 if r.status_code>=400: raise RuntimeError(str(r.status_code)+' '+json.dumps(d)[:1800])
 return d.get('data',d.get('message',d))
def listing(dt,fields,filters=None):
 return call('GET','resource/'+dt,params={'fields':json.dumps(fields),'filters':json.dumps(filters or {}),'limit_page_length':500})
call('POST','method/login',data={'usr':'test@connect4systems.com','pwd':os.environ['SITE_TEST_PASSWORD']})
if __name__=='__main__':
 result={}
 for dt,fields,filters in [
 ('Employee',['name','employee_name','user_id','company','custom_leave_approval_level','custom_first_approval','custom_second_approval','leave_approver','custom_second_leave_approver'],{'status':'Active'}),
 ('Workflow',['name','document_type','is_active'],{'document_type':['in',['Leave Application','Business Trip Request']]}),
 ('Leave Type',['name'],{}),
 ('User',['name','enabled'],{'name':['like','%test%']}),
 ]:
  try: result[dt]=listing(dt,fields,filters)
  except Exception as e: result[dt]=str(e)
 (OUT/'discovery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
