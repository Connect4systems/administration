from probe import *
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 for role,user,route in [('second','noha.saleh@chinaconstruction.com','leave-application/HR-LAP-2026-00015'),('first','ahmed_sabaah@chinaconstruction.com','business-trip-request/5e6f6n28ku')]:
  session=requests.Session(); session.post(BASE+'/api/method/login',data={'usr':user,'pwd':os.environ['SITE_TEST_PASSWORD']},timeout=60).raise_for_status()
  c=b.new_context(viewport={'width':1440,'height':1000})
  c.add_cookies([{'name':x.name,'value':x.value,'domain':x.domain,'path':x.path,'secure':x.secure} for x in session.cookies])
  page=c.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/app/'+route,wait_until='domcontentloaded',timeout=90000)
  page.wait_for_timeout(9000)
  text=page.locator('body').inner_text(); print(role,text[-5000:],flush=True)
  (OUT/(role+'-browser.txt')).write_text(text,encoding='utf-8')
  result=page.evaluate('''async () => { try { const d=await frappe.xcall('frappe.model.workflow.apply_workflow',{doc:cur_frm.doc,action:'Approve'}); return {success:true,state:d.workflow_state}; } catch(e) { return {success:false,error:String(e)}; } }''')
  print('browser approval',role,json.dumps(result)[:1200],flush=True)
  (OUT/(role+'-browser-approval.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
  page.screenshot(path=str(OUT/(role+'-browser.png')),full_page=True)
  (OUT/(role+'-browser-errors.json')).write_text(json.dumps(errors,indent=2))
  c.close()
 b.close()


