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
for role,u in USERS.items():
 SESS[role]=requests.Session()
 check('Login '+role,lambda role=role,u=u:req(role,'method/login',data={'usr':u,'pwd':os.environ['SITE_TEST_PASSWORD']}))
for dt,date in [('Leave Application','2026-10-26'),('Business Trip Request','2026-10-27')]:
 for scenario in ['approve','reject_first','reject_second','reject_hr']:
  try:
   payload={'doctype':dt,'employee':'360','company':'CSCEC','from_date':date,'to_date':date,'description':'TEST 2026-10-20 '+scenario,'reason':'TEST 2026-10-20 '+scenario,'leave_type':'Annual Leave'}
   doc=check(dt+' '+scenario+' create',lambda:req('requester','resource/'+quote(dt),json=payload))
   records.append({'doctype':dt,'name':doc['name'],'scenario':scenario});save()
   assert doc['custom_leave_approval_level']=='Two Level Approval'
   doc=check(dt+' '+scenario+' request',lambda:advance(doc,'requester','Submit for Approval','Pending Approval',0))
   check(dt+' '+scenario+' second cannot approve first stage',lambda:action(doc,'second','Approve'),True)
   check(dt+' '+scenario+' requester cannot approve',lambda:action(doc,'requester','Approve'),True)
   if scenario=='reject_first':
    doc=check(dt+' reject first',lambda:advance(doc,'first','Reject','Rejected',0));continue
   doc=check(dt+' '+scenario+' first approves',lambda:advance(doc,'first','Approve','Pending Management Approval',0))
   check(dt+' '+scenario+' first cannot approve second stage',lambda:action(doc,'first','Approve'),True)
   if scenario=='reject_second':
    doc=check(dt+' reject second',lambda:advance(doc,'second','Reject','Rejected',0));continue
   doc=check(dt+' '+scenario+' second approves',lambda:advance(doc,'second','Approve','Pending HR Approval',0))
   if scenario=='reject_hr':
    doc=check(dt+' reject HR',lambda:advance(doc,'hr','Reject','Rejected',0));continue
   doc=check(dt+' final HR approval',lambda:advance(doc,'hr','Approve','Approved',1))
   records[-1]['approved_verified']=True;save()
   if dt=='Business Trip Request':
    at=listing('Attendance',['name','docstatus','status','attendance_date'],{'custom_business_trip_request':doc['name']})
    check('Trip creates submitted Present attendance',lambda:True if len(at)==1 and at[0]['docstatus']==1 and at[0]['status']=='Present' else (_ for _ in ()).throw(AssertionError(str(at))))
   else:
    le=listing('Leave Ledger Entry',['name','leaves','docstatus'],{'transaction_name':doc['name']})
    check('Annual leave creates debit ledger entry',lambda:True if any(x['leaves']<0 for x in le) else (_ for _ in ()).throw(AssertionError(str(le))))
   doc=check(dt+' HR cancels approved request',lambda:advance(doc,'hr','Cancel','Cancelled',2))
   if dt=='Business Trip Request':
    at=listing('Attendance',['name','docstatus'],{'custom_business_trip_request':doc['name']})
    check('Trip cancellation cancels attendance',lambda:True if at and all(x['docstatus']==2 for x in at) else (_ for _ in ()).throw(AssertionError(str(at))))
  except Exception:
   traceback.print_exc();continue
save()
