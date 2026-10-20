from probe import *
users=['essam_mohamed@chinaconstruction.com','ahmed_sabaah@chinaconstruction.com','noha.saleh@chinaconstruction.com','fady_atef_atta@chinaconstruction.com']
for u in users:
 d=call('GET','resource/User/'+u)
 print(u,'roles',[r['role'] for r in d.get('roles',[])],flush=True)
 call('PUT','resource/User/'+u,json={'new_password':os.environ['SITE_TEST_PASSWORD'],'logout_all_sessions':0})
 print('password reset',u,flush=True)
print('existing leave',listing('Leave Application',['name','from_date','to_date','workflow_state'],{'employee':'360'}))
print('existing attendance',listing('Attendance',['name','attendance_date','status','docstatus'],{'employee':'360','attendance_date':['between',['2026-10-21','2026-11-15']]}))
