from probe import *
R=OUT/'retest';R.mkdir(exist_ok=True)
users=json.loads((OUT/'results.json').read_text())['accounts']
results={}
for role,user in users.items():
 es=listing('Employee',['name','user_id','company','create_user_permission','custom_leave_approval_level','leave_approver','custom_second_leave_approver'],{'user_id':user})
 ps=listing('User Permission',['name','allow','for_value','is_default','apply_to_all_doctypes'],{'user':user})
 results[role]={'employee':es,'permissions':ps}
 print(role,json.dumps(results[role]),flush=True)
(R/'permissions.json').write_text(json.dumps(results,indent=2))
