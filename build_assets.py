"""Sprite slicing, anchor normalization and bidirectional optical-flow inbetweens."""
from pathlib import Path
import sys,json
R=Path(__file__).parent
sys.path.insert(0,str(R/'.tools'))
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage
OUT=R/'baie-native/assets'; OUT.mkdir(exist_ok=True,parents=True)
KEY=R/'source/keyframes';KEY.mkdir(exist_ok=True)
N=384
records={}; groups={}; static={}

def extract(sheet,cols,rows,box=None):
 im=Image.open(R/'source'/sheet).convert('RGBA')
 if box:im=im.crop(box)
 w,h=im.size;out=[]
 for i in range(cols*rows):
  a=np.array(im.crop((round(i%cols*w/cols),round(i//cols*h/rows),round((i%cols+1)*w/cols),round((i//cols+1)*h/rows))))
  lab,n=ndimage.label(a[:,:,3]>32);counts=np.bincount(lab.ravel());counts[0]=0;m=counts.argmax()
  keep=counts>max(80,counts[m]*.004);keep[0]=False
  edge=np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]]))
  for k in edge:
   if k!=m:keep[k]=False
  a[:,:,3]=np.where(keep[lab],a[:,:,3],0)
  y,x=np.where(lab==m);head=x[y<y.min()+(y.max()-y.min())*.5];out.append((Image.fromarray(a),(head.min()+head.max())/2,y.max()+1))
 return out

def normalize(cells,scale,lifted=False):
 out=[]
 for im,cx,bottom in cells:
  im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
  dy=round(366-bottom*scale)
  if lifted:dy=38-im.getbbox()[1]
  canvas=Image.new('RGBA',(N,N));canvas.alpha_composite(im,(round(N/2-cx*scale),dy));out.append(np.array(canvas))
 return out

base=extract('reference.png',4,2)
for name,a in zip(['neutral','talk','happy','wave_seed','smug','sit','side','back'],normalize(base,.64)):
 static[name]=a
for file,names in [('movement.png',['walk','run','jump','dance']),('lift-wave.png',['lift','wave']),('gestures.png',['nod','shake','bow','emotions'])]:
 cols,rows=(4,4) if file=='lift-wave.png' else (4,8)
 cells=extract(file,cols,rows)
 # A single common scale for each entire sheet; seated poses keep their natural shorter height.
 height=Image.open(R/'source'/file).height/rows
 scale=320/(height*.9)
 start=0
 for i,name in enumerate(names):
  count=8
  frames=normalize(cells[start:start+count],scale,lifted=name=='lift');start+=count
  if name=='emotions':
   for label,a in zip(['love','shy','surprised','angry','sad','cry','thinking','wink'],frames):static[label]=a
  else:groups[name]=frames
groups['dizzy']=normalize(extract('interaction.png',8,2,(0,340,1774,630)),2)
groups['rest']=normalize(extract('interaction.png',8,1,(0,630,1774,763)),2.4)

def save(name,a):
 Image.fromarray(a).save(OUT/(name+'.webp'),quality=90,method=4)

def flow(a,b):
 def gray(v):
  rgb=v[:,:,:3].astype(np.float32)*v[:,:,3:4]/255+235*(1-v[:,:,3:4]/255)
  return cv2.cvtColor(rgb.astype('uint8'),cv2.COLOR_RGB2GRAY)
 dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
 return dis.calc(gray(a),gray(b),None)

yy,xx=np.mgrid[:N,:N].astype('float32')
for name,frames in groups.items():
 for i,a in enumerate(frames):
  Image.fromarray(a).save(KEY/f'{name}_{i}.png')
  b=frames[(i+1)%len(frames)];ab=flow(a,b);ba=flow(b,a)
  for j in range(3):
   k=j/3
   if j==0:c=a
   else:
    # Bidirectional motion-compensated warp in premultiplied RGBA prevents matte fringes.
    aa=a.astype('float32')/255;bb=b.astype('float32')/255
    aa[:,:,:3]*=aa[:,:,3:4];bb[:,:,:3]*=bb[:,:,3:4]
    u=cv2.remap(aa,xx-k*ab[:,:,0],yy-k*ab[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    v=cv2.remap(bb,xx-(1-k)*ba[:,:,0],yy-(1-k)*ba[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    # Select the nearer warped source at disoccluding silhouettes: averaging both
    # creates translucent duplicate shoes/hands on large limb movements.
    c=(u if k<.5 else v).copy();c[:,:,:3]/=np.maximum(c[:,:,3:4],.001);c=np.clip(c*255,0,255).astype('uint8')
   save(f'{name}_{i*3+j}',c)
 records[name]={'paintedKeyframes':len(frames),'playbackFrames':len(frames)*3,'method':'bidirectional dense optical-flow; 2 inbetweens per keyframe interval'}
 print(name,flush=True)
for name,a in static.items():save(name,a)
Image.fromarray(static['neutral']).resize((256,256)).save(OUT/'thumb.png')
meta={'size':N,'static':list(static),'sequences':records,'paintedKeyframes':len(static)+sum(len(x) for x in groups.values()),'playbackFrames':len(static)+sum(len(x)*3 for x in groups.values())}
(R/'source/frames.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
keys=[(f'{name}_{i}',a) for name,frames in groups.items() for i,a in enumerate(frames)]
sheet=Image.new('RGB',(8*160,((len(keys)+7)//8)*180),'#eef0f7');d=ImageDraw.Draw(sheet)
for i,(name,a) in enumerate(keys):
 im=Image.fromarray(a).resize((160,160));x=i%8*160;y=i//8*180;sheet.paste(im,(x,y),im);d.text((x+4,y+160),name,fill='#233859')
sheet.save(R/'preview/keyframes.jpg')
print(meta['paintedKeyframes'],meta['playbackFrames'])
