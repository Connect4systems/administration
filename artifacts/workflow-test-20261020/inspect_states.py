from probe import *
r=json.loads((OUT/'results.json').read_text())
for rec in r['records']:
 d=call('GET','resource/'+rec['doctype']+'/'+rec['name']); print(rec['doctype'],rec['name'],{k:d.get(k) for k in ['workflow_state','leave_approver','custom_second_leave_approver','docstatus']})
 print('todos',listing('ToDo',['allocated_to','status'],{'reference_name':rec['name']}))
 print('shares',listing('DocShare',['user','read','write'],{'share_name':rec['name']}))
(OUT/'initial-results.json').write_text(json.dumps(r,indent=2))
