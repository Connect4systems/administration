from probe import *
import re,traceback
from urllib.parse import quote
USERS={'requester':'essam_mohamed@chinaconstruction.com','first':'ahmed_sabaah@chinaconstruction.com','second':'noha.saleh@chinaconstruction.com','hr':'fady_atef_atta@chinaconstruction.com'}
SESS={}; results=[]; records=[]
def save():
 (OUT/'results.json').write_text(json.dumps({'accounts':USERS,'checks':results,'records':records},indent=2),encoding='utf-8')
def req(role,path,method='POST',**kw):
 r=SESS[role].request(method,BASE+'/api/'+path,timeout=60,**kw)
 d=r.json()
 if r.status_code>=400: raise RuntimeError(str(r.status_code)+' '+str(d.get('_server_messages') or d.get('exception')))
 return d.get('data',d.get('message',d))
def check(label,fn,denied=False):
 try:
  v=fn()
  if denied: raise AssertionError('Unauthorized operation succeeded')
  results.append({'check':label,'passed':True}); print('PASS',label,flush=True);save();return v
 except Exception as e:
  ok=denied and not isinstance(e,AssertionError) and any(t in str(e) for t in ['403','417','Permission','WorkflowTransition','not allowed','not a valid'])
  results.append({'check':label,'passed':ok,'detail':str(e)[:1500]});print('PASS' if ok else 'FAIL',label,str(e)[:400],flush=True);save()
  if not denied: raise

def getdoc(dt,name,role='requester'): return req(role,'resource/'+quote(dt)+'/'+quote(name),method='GET')
def action(doc,role,act):
 return req(role,'method/frappe.model.workflow.apply_workflow',data={'doc':json.dumps(doc),'action':act})
def advance(doc,role,act,state,ds):
 updated=action(doc,role,act)
 assert updated['workflow_state']==state and updated['docstatus']==ds,(updated['workflow_state'],updated['docstatus'])
 assert updated['status']==(state if state in ['Approved','Rejected','Cancelled'] else 'Open')
 return updated

OUT=OUT/'approval-retest'; OUT.mkdir(exist_ok=True)

for role,u in USERS.items():
 SESS[role]=requests.Session()
 check('Login '+role,lambda role=role,u=u:req(role,'method/login',data={'usr':u,'pwd':os.environ['SITE_TEST_PASSWORD']}))
for dt,date in [('Leave Application','2026-10-19'),('Business Trip Request','2026-10-20')]:
 try:
  payload={'doctype':dt,'employee':'360','company':'CSCEC','from_date':date,'to_date':date}
  if dt=='Leave Application': payload.update({'leave_type':'Annual Leave','description':'TEST approval and attendance retest 2026-10-20'})
  else: payload['reason']='TEST approval and attendance retest 2026-10-20'
  doc=check(dt+' create',lambda:req('requester','resource/'+quote(dt),json=payload))
  records.append({'doctype':dt,'name':doc['name'],'date':date});save()
  doc=check(dt+' submit for approval',lambda:advance(doc,'requester','Submit for Approval','Pending Approval',0))
  for role,state,ds in [('first','Pending Management Approval',0),('second','Pending HR Approval',0),('hr','Approved',1)]:
   doc=check(dt+' '+role+' approval',lambda role=role,state=state,ds=ds:advance(doc,role,'Approve',state,ds))
  records[-1]['final_state']=doc['workflow_state'];records[-1]['docstatus']=doc['docstatus'];save()
  link='leave_application' if dt=='Leave Application' else 'custom_business_trip_request'
  rows=listing('Attendance',['name','attendance_date','status','docstatus',link],{link:doc['name']})
  records[-1]['attendance']=rows;save()
  expected='On Leave' if dt=='Leave Application' else 'Present'
  check(dt+' creates linked submitted '+expected+' attendance',lambda:True if len(rows)==1 and rows[0]['status']==expected and rows[0]['docstatus']==1 and rows[0]['attendance_date']==date else (_ for _ in ()).throw(AssertionError(json.dumps(rows))))
  if dt=='Leave Application':
   rows=listing('Leave Ledger Entry',['name','leaves','docstatus'],{'transaction_name':doc['name']})
   records[-1]['ledger']=rows;save()
   check('Annual leave debit ledger',lambda:True if any(x['leaves']<0 and x['docstatus']==1 for x in rows) else (_ for _ in ()).throw(AssertionError(json.dumps(rows))))
 except Exception:
  traceback.print_exc();continue
save()
