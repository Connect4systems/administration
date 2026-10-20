from probe import *
print(listing('Leave Allocation',['employee','total_leaves_allocated'],{'employee':['in',['360','369','421','441','450','490','495','633','777','871','878']],'leave_type':'Annual Leave','docstatus':1}))
u='fady_atef_atta@chinaconstruction.com'; d=call('GET','resource/User/'+u); print(u,d['enabled'],[r['role'] for r in d.get('roles',[])])
