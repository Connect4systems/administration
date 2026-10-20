from probe import *
for dt,fields,filters in [('Leave Application',['name','from_date','to_date','workflow_state','docstatus'],{'employee':'360'}),('Attendance',['name','attendance_date','status','docstatus','leave_application','custom_business_trip_request'],{'employee':'360','attendance_date':['between',['2026-10-15','2026-10-27']]})]:
 print(dt,json.dumps(listing(dt,fields,filters)),flush=True)
