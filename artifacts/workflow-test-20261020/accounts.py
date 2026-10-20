from probe import *
for dt,fields,filters in [('Leave Allocation',['name','employee','total_leaves_allocated'],{'employee':'330','leave_type':'Annual Leave','docstatus':1}),('User',['name'],[['Has Role','role','=','HR Leave Approver']])]:
 try: print(dt,json.dumps(listing(dt,fields,filters)))
 except Exception as e: print(str(e))
for u in ['david_maher@chinaconstruction.com','ahmed_sabaah@chinaconstruction.com','christina_magdy@chinaconstruction.com']:
 d=call('GET','resource/User/'+u); print(u, d['enabled'],[r['role'] for r in d.get('roles',[])])
print('leave records',listing('Leave Application',['name','from_date','to_date','status','workflow_state'],{'employee':'330'}))
