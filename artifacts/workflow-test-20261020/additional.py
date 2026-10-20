from probe import *
checks=[]
def record(label,ok,detail):
 checks.append({'check':label,'passed':ok,'detail':detail});print(label,ok,str(detail)[:200],flush=True)
a=requests.Session();a.post(BASE+'/api/method/login',data={'usr':'essam_mohamed@chinaconstruction.com','pwd':os.environ['SITE_TEST_PASSWORD']},timeout=60).raise_for_status()
for dt,name,payload,label in [
 ('Business Trip Request','5e6f6n28ku',{'reason':'TEST attempted edit after requesting approval'},'Trip details immutable after requesting'),
 ('Leave Application','HR-LAP-2026-00015',{'custom_leave_approval_level':'No Approval Required'},'Annual leave approval snapshot immutable'),
 ('Business Trip Request','5e6f6n28ku',{'custom_second_leave_approver':'test@connect4systems.com'},'Trip approval snapshot immutable')]:
 r=a.put(BASE+'/api/resource/'+dt+'/'+name,json=payload,timeout=60);d=r.json();record(label,r.status_code>=400,{'code':r.status_code,'error':d.get('_server_messages')})
for dt,name in [('Leave Application','HR-LAP-2026-00015'),('Business Trip Request','5e6f6n28ku')]:
 todos=listing('ToDo',['allocated_to','status'],{'reference_name':name,'status':'Open'})
 record(dt+' one current-stage assignment',len(todos)==1,todos)
 if dt=='Business Trip Request':
  rows=listing('Attendance',['name'],{'custom_business_trip_request':name}); record('No attendance before final trip approval',not rows,rows)
 else:
  rows=listing('Leave Ledger Entry',['name'],{'transaction_name':name});record('No leave debit before final HR approval',not rows,rows)
(OUT/'additional-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
