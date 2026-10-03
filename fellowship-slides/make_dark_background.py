"""Build assets/background-dark.png from assets/background.png (run from fellowship-slides/)."""
import numpy as np, cv2
from PIL import Image
rgb=np.array(Image.open('assets/background.png').convert('RGB')).astype(np.float32)/255
H,W=rgb.shape[:2]
lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)
L=lab[...,0]
# soften the original sparkles first so the inversion doesn't leave dark ghosts
mask=np.zeros((H,W),np.float32)
for cx,cy in [(215,215),(830,1515)]:
    cv2.circle(mask,(cx,cy),175,1,-1)
mask=cv2.GaussianBlur(mask,(0,0),25)
Lsoft=cv2.medianBlur(np.clip(L*2.55,0,255).astype(np.uint8),151).astype(np.float32)/2.55
Lsoft=cv2.GaussianBlur(Lsoft,(0,0),15)
L=L*(1-mask)+np.minimum(L,Lsoft)*mask
out=lab.copy()
out[...,0]=7+(100-L)*0.85
out[...,1]*=1.4
out[...,2]=lab[...,2]*1.4-6
dark=np.clip(cv2.cvtColor(out,cv2.COLOR_LAB2RGB),0,1)

# redraw the sparkles as four-point stars with a soft glow
S=4
def star(cx,cy,rx,ry):
    t=np.linspace(0,2*np.pi,720)
    x=cx+rx*np.sign(np.cos(t))*np.abs(np.cos(t))**4
    y=cy+ry*np.sign(np.sin(t))*np.abs(np.sin(t))**4
    return np.stack([x,y],1)
big=np.zeros((H*S,W*S),np.uint8)
for (cx,cy,rx,ry) in [(215,215,128,110),(830,1515,118,120)]:
    pts=(star(cx,cy,rx,ry)*S).astype(np.int32)
    cv2.fillPoly(big,[pts],255,lineType=cv2.LINE_AA)
shape=cv2.resize(big,(W,H),interpolation=cv2.INTER_AREA).astype(np.float32)/255
shape=cv2.GaussianBlur(shape,(0,0),1.0)
glow=cv2.GaussianBlur(shape,(0,0),10)*1.2+cv2.GaussianBlur(shape,(0,0),35)*0.9
a=np.clip(np.maximum(shape,glow),0,1)[...,None]
dark=dark*(1-a)+np.array([1,1,1])*a
Image.fromarray((dark*255).round().astype(np.uint8)).save('assets/background-dark.png')
