import asyncio,json,base64,io
from PIL import Image
from pathlib import Path
from playwright.async_api import async_playwright
R=Path(__file__).parent
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  page=await browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto((R/'dist/baie-preview.html').as_uri())
  await page.wait_for_function('window.qa?.ready',timeout=60000)
  await page.evaluate('qa.manual(true)')
  print('Initial:',await page.evaluate('qa.snapshot()'))
  results=await page.evaluate('''async()=>{
   const out=[];
   for(const v of qa.payload.vocab){
    await qa.reset();const accepted=qa.body.do(v.id);let poses=new Set(),modes=new Set();
    for(let i=0;i<200;i++){qa.advance();poses.add(qa.snapshot().pose);modes.add(qa.body.layout().mode)}
    out.push({word:v.id,accepted,poses:[...poses],modes:[...modes]});
   }return out;
  }''')
  print('Words:',len(results),'accepted:',sum(x['accepted'] for x in results))
  interaction=await page.evaluate('''async()=>{
   await qa.reset();const b=qa.body;let tm=1000;
   const events=()=>[...qa.events];
   const pos=()=>{const a=b.layout().hit[0];return {x:a.x,y:a.y,t:tm}};
   // Poke through the same pointer interface that the native host forwards.
   let p=pos();b.pointer('down',p);tm+=90;b.pointer('up',{...p,t:tm});qa.advance(120);
   const poke=events();await qa.reset();const c=qa.body;
   // Many strokes of the head trigger the native pat reflex.
   const h=c.layout().hit[0];for(let i=0;i<32;i++){tm+=30;c.pointer('move',{x:h.x+(i%2?25:-25),y:h.y,t:tm});qa.advance(2)}
   const pat=events();await qa.reset();const d=qa.body;
   const a=d.layout().hit[0];d.pointer('down',{x:a.x,y:a.y,t:tm});tm+=40;d.pointer('move',{x:a.x+15,y:a.y-50,t:tm});qa.advance(25);
   const lifted=qa.snapshot();const liftPoses=[];for(let i=0;i<60;i++){qa.advance();liftPoses.push(qa.snapshot().pose)}
   // Lift high, then throw downward fast enough to exercise the actual crash threshold.
   tm+=100;d.pointer('move',{x:a.x+30,y:80,t:tm});qa.advance(30);
   tm+=30;d.pointer('move',{x:a.x+60,y:170,t:tm});tm+=10;d.pointer('up',{x:a.x+70,y:200,t:tm});
   let throwModes=new Set(),throwPoses=new Set();for(let i=0;i<300;i++){qa.advance();throwModes.add(d.layout().mode);throwPoses.add(qa.snapshot().pose)}
   const thrown=events();await qa.reset();qa.body.do('sleep');qa.advance(100);
   const before=qa.body.layout();const s=before.hit[0];qa.body.pointer('down',{x:s.x,y:s.y,t:tm+100});qa.body.pointer('up',{x:s.x,y:s.y,t:tm+190});qa.advance(1);
   const wake=qa.snapshot();return {poke,pat,lifted,liftPoses:[...new Set(liftPoses)],throwModes:[...throwModes],throwPoses:[...throwPoses],thrown,wake,before};
  }''')
  print('Interaction:',json.dumps(interaction,ensure_ascii=False))
  await page.evaluate('qa.reset()');await page.screenshot(path=str(R/'preview'/'runtime.png'),full_page=True)
  report={'errors':errors,'words':results,'interactions':interaction}
  (R/'preview'/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
  print('Errors:',errors)
  assert not errors
  assert all(x['accepted'] for x in results)
  assert len(interaction['liftPoses'])>=8,interaction['liftPoses']
  assert all(m in interaction['throwModes'] for m in ['air','dizzy','idle'])
  assert any(e['kind']=='crash' for e in interaction['thrown'])
  assert any(e['kind']=='pet' for e in interaction['pat'])
  assert any(e.get('woke') for e in interaction['wake']['events'])
  # A compact animated contact sheet of the four key painted animation cycles.
  await page.evaluate('''async()=>{qa.images=Object.fromEntries(await Promise.all(qa.mod.ASSETS.map(async n=>[n,await qa.loadImage(qa.payload.images[n+'.webp'])])))}''')
  frames=[]
  for i in range(72):
   data=await page.evaluate('''i=>{
    const out=document.createElement('canvas');out.width=640;out.height=680;const c=out.getContext('2d');
    c.fillStyle='#eaf0fa';c.fillRect(0,0,640,680);
    const names=['提起 · 挣动分帧','头晕 · 坐倒失衡','行走 · 迈步循环','跳舞 · 手脚动作'];
    for(let j=0;j<4;j++){
      const temp=document.createElement('canvas');temp.width=temp.height=512;
      qa.mod.paint(temp.getContext('2d'),qa.images,{mode:['drag','dizzy','walk','dance'][j],face:['dragged','dizzy','neutral','happy'][j],t:i/24,modeT:(i/24)%2.2,facing:1,talk:0,look:[0,0]});
      const x=j%2*320,y=Math.floor(j/2)*340;c.drawImage(temp,x,y,320,320);
      c.fillStyle='#2f4e77';c.font='16px Microsoft YaHei';c.textAlign='center';c.fillText(names[j],x+160,y+332);
    }return out.toDataURL('image/png').split(',')[1];
   }''',i)
   frames.append(Image.open(io.BytesIO(base64.b64decode(data))).convert('RGB'))
  frames[0].save(R/'preview/interactions.gif',save_all=True,append_images=frames[1:],duration=42,loop=0,optimize=True)
  await browser.close()
asyncio.run(main())
