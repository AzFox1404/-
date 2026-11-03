"""Bounded viewport tiles for oversized sheets; page geometry stays canonical."""
from collections import OrderedDict
from PIL import Image,ImageTk

class Tiles:
    def __init__(self,view):
        self.v=view;self.cache=OrderedDict();self.bytes=0;self.signature=None;self.visible={};self.pending=set();self.serial=0
        self.overviews=OrderedDict();self.overview_pending=set();self.backdrops={};self.text_pending=set()
    def reset(self,content=False):
        if self.v.canvas.winfo_exists():self.v.canvas.delete('pdf-tile');self.v.canvas.delete('pdf-overview')
        self.visible.clear();self.backdrops.clear();self.signature=None;self.pending.clear();self.text_pending.clear()
        if content:self.cache.clear();self.bytes=0;self.overviews.clear();self.overview_pending.clear()
    def large(self,n):return self.v.pages[n][1]*self.v.pages[n][2]>3_000_000
    def update(self,pages):
        v=self.v;c=v.canvas;wanted=[]
        left=max(0,int(c.canvasx(0)-8));right=left+max(1,c.winfo_width())
        top=c.canvasy(0);bottom=top+max(1,c.winfo_height())
        for n in pages:
            if not self.large(n):continue
            y,w,h,_=v.pages[n];a=max(0,int(top-y));b=min(h,int(bottom-y)+1)
            okey=(n,v.rotations.get(str(n),0))
            if okey in v._text_cache:v.selection.pages[n]=dict(x=8,y=y,w=w,h=h,chars=v._text_cache[okey],rotation=okey[1])
            if okey not in self.overviews and okey not in self.overview_pending:
                self.overview_pending.add(okey)
                z=min(75,800/max(v._sizes[n])*75)
                v.renderer.jobs.put(dict(op='page',generation=v._generation,epoch=v._epoch,page=n,zoom=z,rotation=okey[1],overview=True,text=False))
            if okey in self.overviews and b>a:
                im=self.overviews[okey];x0=min(w,left);x1=min(w,right)
                if x1>x0:
                    crop=im.crop((x0/w*im.width,a/h*im.height,x1/w*im.width,b/h*im.height)).resize((x1-x0,b-a),Image.Resampling.BILINEAR)
                    photo=ImageTk.PhotoImage(crop,master=c);c.delete('overview'+str(n))
                    item=c.create_image(8+x0,y+a,image=photo,anchor='nw',tags=('pdf-overview','overview'+str(n)))
                    c.tag_lower(item);c.tag_raise(item,v.pages[n][3]);self.backdrops[n]=photo
            for ty in range(a//512*512,b,512):
                for tx in range(left//512*512,min(w,right+1),512):wanted.append((n,v.zoom,v.rotations.get(str(n),0),tx,ty,min(tx+512,w),min(ty+512,h)))
        signature=tuple(wanted)
        if signature!=self.signature:
            self.signature=signature;self.serial+=1;v.renderer.set_viewport(self.serial,pages);self.pending.clear();self.text_pending.clear()
            self.overview_pending={k for k in self.overview_pending if k[0] in pages}
        keep=set(wanted)
        for key,item in list(self.visible.items()):
            if key not in keep:c.delete(item[0]);del self.visible[key]
        for key in wanted:
            if key in self.visible:continue
            if key in self.cache:self.draw(key,self.cache[key]);continue
            if key in self.pending:continue
            self.pending.add(key);n,z,r,x,y,x1,y1=key
            text=(n,r) not in v._text_cache and (n,r,self.serial) not in self.text_pending
            if text:self.text_pending.add((n,r,self.serial))
            v.renderer.tile(v._generation,v._epoch,n,z,r,(x,y,x1,y1),self.serial,text=text)
    def overview(self,result):
        key=(result['page'],result['rotation']);self.overview_pending.discard(key)
        self.overviews[key]=Image.frombytes('RGB',result['size'],result['rgb'])
        while len(self.overviews)>4:self.overviews.popitem(last=False)
        self.v.schedule_visible()
    def draw(self,key,photo):
        v=self.v;n,z,r,x,y,_,_=key
        item=v.canvas.create_image(8+x,v.pages[n][0]+y,image=photo,anchor='nw',tags=('pdf-tile',))
        self.visible[key]=(item,photo)
    def receive(self,result):
        v=self.v
        if result['viewport']!=self.serial:return
        n=result['page'];key=(n,result['zoom'],result['rotation'],*result['tile']);self.pending.discard(key)
        im=Image.frombytes('RGB',result['size'],result['rgb']);photo=ImageTk.PhotoImage(im,master=v.canvas);im.close()
        if key not in self.cache:self.bytes+=photo.width()*photo.height()*4
        self.cache[key]=photo;self.cache.move_to_end(key)
        while self.bytes>48*1024*1024 and self.cache:
            _,old=self.cache.popitem(last=False);self.bytes-=old.width()*old.height()*4
        if key not in self.visible:self.draw(key,photo)
        chars=result['chars'] or v._text_cache.get((n,key[2]),[])
        v._text_cache[(n,key[2])]=chars
        y,w,h,_=v.pages[n];v.selection.pages[n]=dict(x=8,y=y,w=w,h=h,chars=chars,rotation=key[2])
        v.selection.highlight();v.draw_quick()
