from probe import *
for dt,fields,filters in [
 ('Employee',['name','employee_name','user_id','company','custom_leave_approval_level','custom_first_approval','custom_second_approval','leave_approver','custom_second_leave_approver'],{'custom_leave_approval_level':'Two Level Approval','user_id':['is','set']}),
 ('Leave Allocation',['name','employee','from_date','to_date','total_leaves_allocated','docstatus'],{'leave_type':'Annual Leave','docstatus':1,'to_date':['>=','2026-10-20']}),
 ('Has Role',['parent','role'],{'role':'HR Leave Approver'}),
]:
 try: print(dt,json.dumps(listing(dt,fields,filters)))
 except Exception as e: print(dt,str(e))
