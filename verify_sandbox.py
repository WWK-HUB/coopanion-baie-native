"""Run the shipped software's unmodified figure-frame with its actual opaque-origin CSP."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from threading import Thread
import asyncio,json,mimetypes,os
from playwright.async_api import async_playwright
R=Path(__file__).parent
WEB=Path(os.environ.get('COOPANION_APP_DIR','D:/pet/coo1/Coopanion/resources/app'))/'node_modules/cortico-world-desktop-pet/web'
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  url=urlsplit(self.path).path
  if url=='/':
   content=b'''<!doctype html><body style="margin:0;background:#edf1fa"><iframe style="border:0;width:900px;height:650px" src="/figure-frame?pack=baie-native"></iframe><script>window.messages=[];addEventListener('message',e=>{messages.push(e.data);if(e.data.t==='loaded')e.source.postMessage({t:'init',entry:location.origin+'/packs/baie-native/figure.js',export:'createBaie',base:location.origin+'/packs/baie-native/',start:{x:450,facing:1},bounds:{W:900,H:650,floorY:600,S:1.4},language:'zh',theme:'light'},'*')});window.send=m=>document.querySelector('iframe').contentWindow.postMessage(m,'*')</script>'''
  else:
   p=WEB/'figure-frame.html' if url=='/figure-frame' else WEB/url[5:] if url.startswith('/web/') else R/'baie-native'/url[len('/packs/baie-native/'):] if url.startswith('/packs/baie-native/') else None
   if p is None or '..' in url or not p.is_file():self.send_error(404);return
   content=p.read_bytes()
  self.send_response(200)
  self.send_header('Content-Type','text/html' if url in ['/','/figure-frame'] else 'text/javascript' if url.endswith('.js') else mimetypes.guess_type(url)[0] or 'application/octet-stream')
  self.send_header('Access-Control-Allow-Origin','*')
  if url=='/figure-frame':
   origin='http://'+self.headers['Host']
   self.send_header('Content-Security-Policy',f"sandbox allow-scripts; default-src 'none'; script-src {origin}; img-src {origin} data: blob:; style-src 'unsafe-inline'; connect-src {origin}/packs/baie-native/; frame-ancestors {origin} http://127.0.0.1:* http://localhost:*")
  self.end_headers();self.wfile.write(content)
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start()
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':900,'height':650})
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto('http://127.0.0.1:'+str(server.server_port))
   await page.wait_for_function("messages.some(m=>m.t==='ready'||m.t==='error')",timeout=60000)
   ready=await page.evaluate("messages.find(m=>m.t==='ready'||m.t==='error')")
   assert ready['t']=='ready',ready
   await page.evaluate("send({t:'set',state:{roam:'off'}});send({t:'do',word:'wave'});for(let i=0;i<45;i++)send({t:'tick',dt:1/60})")
   await page.wait_for_function("messages.some(m=>m.t==='frame')")
   await page.wait_for_timeout(300)
   await page.screenshot(path=str(R/'preview'/'native-sandbox.png'))
   frame=page.frames[1]
   pose=await frame.locator('canvas').get_attribute('data-pose')
   report={'native_frame':'unmodified figure-frame.js','csp':'sandbox allow-scripts; opaque origin; native script/img/connect restrictions','ready':ready,'renderedPose':pose,'errors':errors,'protocolErrors':await page.evaluate("messages.filter(m=>m.t==='error')")}
   (R/'preview'/'native-sandbox-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
   assert pose.startswith('wave_'),pose
   assert not errors and not report['protocolErrors'],report
   print('Native sandbox PASS; words:',len(ready['words']),'painted:',pose)
   await browser.close()
 finally:server.shutdown();server.server_close()
asyncio.run(main())
