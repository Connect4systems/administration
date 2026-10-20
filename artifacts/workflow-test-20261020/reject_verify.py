from probe import *
from urllib.parse import quote
checks=[]
def asuser(user):
 x=requests.Session(); x.post(BASE+'/api/method/login',data={'usr':user,'pwd':os.environ['SITE_TEST_PASSWORD']},timeout=60).raise_for_status();return x
app=asuser('essam_mohamed@chinaconstruction.com'); first=asuser('ahmed_sabaah@chinaconstruction.com')
def post(session,path,data=None,payload=None):
 r=session.post(BASE+'/api/'+path,data=data,json=payload,timeout=60); d=r.json();return r.status_code,d.get('data',d.get('message',d))
payload={'doctype':'Leave Application','employee':'360','company':'CSCEC','from_date':'2026-10-28','to_date':'2026-10-28','leave_type':'Annual Leave','description':'TEST 2026-10-20 first rejection'}
code,d=post(app,'resource/Leave Application',payload=payload);print('create',code,d.get('name'),flush=True)
if code==200:
 name=d['name']
 for sess,action in [(app,'Submit for Approval'),(first,'Reject')]:
  code,d=post(sess,'method/frappe.model.workflow.apply_workflow',data={'doc':json.dumps(d),'action':action});print(action,code,d.get('workflow_state'),flush=True)
  checks.append({'action':action,'code':code,'state':d.get('workflow_state'),'name':name})
 print('remaining assignments',listing('ToDo',['status','allocated_to'],{'reference_name':name}))
(OUT/'rejection-check.json').write_text(json.dumps(checks,indent=2))
