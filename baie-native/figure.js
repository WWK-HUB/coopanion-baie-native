/** 白厄 — original keyframes with offline bidirectional optical-flow inbetweens. */
const NS='http://www.w3.org/2000/svg';
export const COUNTS={walk:24,run:24,jump:24,dance:24,lift:24,dizzy:48,rest:24,wave:24,nod:24,shake:24,bow:24};
export const STATIC=['neutral','talk','happy','wave_seed','smug','sit','side','back','love','shy','surprised','angry','sad','cry','thinking','wink'];
export const ASSETS=[...STATIC,...Object.entries(COUNTS).flatMap(([p,n])=>Array.from({length:n},(_,i)=>`${p}_${i}`))];
const clip=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const cycle=(p,t,speed=24)=>`${p}_${Math.floor(t*speed)%COUNTS[p]}`;
const once=(p,k)=>`${p}_${Math.min(COUNTS[p]-1,Math.floor(clip(k)*COUNTS[p]))}`;
const facePose={neutral:'neutral',happy:'happy',wink:'wink',love:'love',shy:'shy',surprised:'surprised',angry:'angry',sad:'sad',sleepy:'rest_12',thinking:'thinking',smug:'smug',pout:'angry',worried:'sad',determined:'smug',flustered:'shy',scared:'surprised',excited:'talk',cry:'cry',confused:'thinking',listening:'neutral',content:'sit',bowing:'bow_12',waking:'rest_18',squeeze:'happy'};
export function selectFrame(f){
 const t=f.t||0,mt=f.modeT||0,g=f.gesture;let pose=facePose[f.face]||'neutral';
 if(f.mode==='drag')pose=cycle('lift',mt);
 else if(f.mode==='dizzy')pose=mt<2.4?cycle('dizzy',mt):once('shake',(mt-2.4)/.6);
 else if(f.mode==='air')pose=f.thrown||f.face==='dragged'?'dizzy_0':g?.kind==='flap'?cycle('wave',mt,30):'jump_12';
 else if(f.mode==='crouch')pose=once('jump',mt/.16*.35);
 else if(f.mode==='land')pose=once('jump',.75+mt/.4*.25);
 else if(g&&['nod','shake','bow','wave'].includes(g.kind))pose=once(g.kind,g.k);
 else if(g?.kind==='spin')pose=g.k<.2?'neutral':g.k<.4?'side':g.k<.7?'back':g.k<.9?'side':'neutral';
 else if(g?.kind==='hug')pose='love';
 else if(g?.kind==='prone')pose=once('rest',.25+.35*Math.sin(g.k*Math.PI));
 else if(g?.kind==='stretch')pose=once('rest',.75+g.k*.25);
 else if(f.mode==='walk')pose=cycle('walk',mt);
 else if(f.mode==='run')pose=cycle('run',mt,30);
 else if(f.mode==='dance')pose=cycle('dance',mt);
 else if(f.mode==='sleep')pose=mt<.8?once('rest',mt/.8*.58):'rest_12';
 else if(f.mode==='sit')pose=mt<.5?once('rest',mt/.5*.25):'sit';
 else if(f.mode==='wake')pose=f.face==='surprised'?once('jump',mt/.9):once('rest',.65+mt/1.8*.35);
 else if(f.mode==='look')pose=cycle('shake',mt,18);
 else if(g?.kind==='shiver')pose='sad';
 else if(Math.abs(f.facing??1)<.75)pose='side';
 else if(f.face==='neutral'&&f.talk>.12)pose=Math.floor(t*12)%3?'talk':'neutral';
 else if(f.face==='neutral'&&f.blink>.7)pose='happy';
 return{pose,mirror:g?.kind==='spin'&&g.k>.7&&g.k<.9};
}
export function paint(ctx,images,f){
 const {pose,mirror}=selectFrame(f);const im=images[pose];if(!im)throw Error('Missing frame '+pose);
 ctx.clearRect(0,0,512,512);ctx.save();if(mirror){ctx.translate(512,0);ctx.scale(-1,1);}
 const calm=['idle','sit','sleep'].includes(f.mode)&&!f.gesture;
 const breath=calm?Math.sin((f.t||0)*1.9):0;
 // Tiny part deformation adds breathing; major actions use the full precomputed frame sequences.
 for(let y=0;y<384;y+=4){const k=Math.max(0,1-Math.abs(y-170)/170);let x=(f.look?.[0]||0)*k*.25;if(f.gesture?.kind==='shiver')x+=Math.sin(f.t*65)*k;ctx.drawImage(im,0,y,384,4,x,y*512/384+breath*k,512,4*512/384+.25);}
 ctx.restore();return pose;
}
export async function createBaie(base,{kit,host,loadImage,asset}){
 const images=Object.fromEntries(await Promise.all(ASSETS.map(async n=>[n,await loadImage(asset(`assets/${n}.webp`))])));
 const doc=host.root.ownerDocument;
 const group=doc.createElementNS(NS,'g');group.setAttribute('class','baie-native');
 const fo=doc.createElementNS(NS,'foreignObject');
 fo.setAttribute('x','0');fo.setAttribute('y','12');fo.setAttribute('width','256');fo.setAttribute('height','256');fo.style.overflow='visible';
 const canvas=doc.createElementNS('http://www.w3.org/1999/xhtml','canvas');canvas.width=canvas.height=512;canvas.style.cssText='display:block;width:256px;height:256px;pointer-events:none';
 fo.appendChild(canvas);group.appendChild(fo);
 const ctx=canvas.getContext('2d');
 let previousMode='idle',thrown=false,currentPose='neutral';
 const lying=()=>/^rest_(9|1[0-7])$/.test(currentPose);
 const sitting=()=>currentPose==='sit'||currentPose.startsWith('dizzy_')||/^rest_[6-8]$/.test(currentPose);
 const figure={
   draw(parent,face,fr){
     if(fr.mode==='air'&&previousMode!=='air')thrown=previousMode==='drag';
     if(fr.mode!=='air')thrown=false;
     previousMode=fr.mode;
     if(group.parentNode!==parent){parent.textContent='';parent.appendChild(group);}
     currentPose=paint(ctx,images,{...fr,thrown});canvas.dataset.pose=currentPose;canvas.dataset.mode=fr.mode;
   },
   gestures:['nod','shake','spin','wave','bow','flap','shiver'],
   groupTilt(mode,tilt,lean){return ['dizzy','sleep','sit','dance'].includes(mode)?0:mode==='drag'?tilt*.4:tilt+lean;},
   get anchors(){const top=lying()?143:sitting()?90:28;return{gaze:[128,top+90],tear:[112,top+110],tears:[[110,top+110],[148,top+110]],z:[203,top+5],hearts:[92,170,top],bubble:[128,top-15]};},
   get extent(){return lying()?[36,143,223,256]:sitting()?[43,90,223,256]:[48,28,217,256];},
   get hits(){return lying()?[[100,212,48],[170,227,43]]:sitting()?[[128,162,65],[128,220,49]]:[[128,110,72],[128,200,57]];},
   colors:{z:'#79a9e9'},
 };
 const body=kit.createBody(host,{figure,css:':root{--skin-eye:#79a9e9;--heart:#ff739a;--tear:#79c9fa}',words:{hug:{motion:{seconds:2.8,face:'love'}},prone:{motion:{seconds:3,face:'happy'}},stretch:{motion:{seconds:2.4,face:'happy'}}}});
 // Exposed only as DOM data in the sandbox: useful for the shipped preview and visual QA.
 return body;
}
