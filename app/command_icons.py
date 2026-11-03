"""Small line icons for the quick-access strip, drawn once per colour theme."""
from PIL import Image,ImageDraw,ImageTk

def command_icon(master,name,color):
    scale=4
    im=Image.new('RGBA',(20*scale,20*scale));d=ImageDraw.Draw(im)
    def line(*pts):d.line([(int(x*scale),int(y*scale)) for x,y in pts],fill=color,width=6,joint='curve')
    def box(x,y,r,b):d.rounded_rectangle(tuple(int(i*scale) for i in (x,y,r,b)),radius=4,outline=color,width=5)
    if name=='feather':
        line((4,18),(15,3),(18,2),(17,8),(11,14),(7,14));line((8,11),(13,8));line((10,8),(14,5))
    elif name=='import':
        line((2,8),(2,5),(7,5),(9,7),(16,7),(16,9));line((2,8),(5,15),(16,15),(18,9),(7,9),(5,15))
    elif name=='export':
        line((9,5),(3,5),(3,16),(15,16),(15,11));line((9,11),(17,3));line((11,3),(17,3),(17,9))
    elif name=='assemble':
        line((3,6),(10,2),(17,6),(10,10),(3,6));line((3,10),(10,14),(17,10));line((3,14),(10,18),(17,14))
    elif name=='print':
        box(5,2,15,8);box(2,7,18,14);box(5,11,15,18);line((14,9),(16,9))
    elif name=='help':
        d.ellipse((8,8,72,72),outline=color,width=5);line((7,7),(8,5),(11,5),(13,7),(12,9),(10,10),(10,12));line((10,14),(10,15))
    elif name in ('undo','redo'):
        pts=[(3,9),(11,9),(14,10),(16,12),(16,15)];arrow=[(7,5),(3,9),(7,13)]
        if name=='redo':pts=[(20-x,y) for x,y in pts];arrow=[(20-x,y) for x,y in arrow]
        line(*pts);line(*arrow)
    elif name=='copy':
        box(7,6,17,17);line((13,4),(13,2),(3,2),(3,13),(5,13))
    elif name=='paste':
        box(4,4,16,18);box(7,2,13,6);line((7,10),(13,10));line((7,13),(12,13))
    elif name=='cut':
        for x in [5,13]:d.ellipse(((x-2)*scale,12*scale,(x+2)*scale,16*scale),outline=color,width=5)
        line((6,12),(15,3));line((12,12),(4,3))
    elif name=='minimize':line((4,13),(16,13))
    elif name=='windowmax':box(4,4,16,16)
    elif name=='detach':
        line((4,10),(4,16),(11,16));line((8,12),(16,4));line((10,4),(16,4),(16,10))
    elif name in ('fullscreen','restore'):
        for dx,dy in [(1,1),(-1,1),(-1,-1),(1,-1)]:
            xy=lambda a,b:(10+dx*a,10+dy*b)
            edge,inner=(7,3) if name=='fullscreen' else (3,7)
            line(xy(inner,edge),xy(edge,edge),xy(edge,inner))
    elif name in ('left','right','up','down'):
        points=[(12,4),(6,10),(12,16)]
        if name=='right':points=[(20-x,y) for x,y in points]
        if name=='up':points=[(y,x) for x,y in points]
        if name=='down':points=[(y,20-x) for x,y in points]
        line(*points)
    elif name in ('rotateleft','rotateright'):
        # One arrow is obtained by mirroring the other, keeping the head on the arc.
        direction=-1 if name=='rotateleft' else 1
        import math
        points=[(10+6*math.cos(math.radians(a)),10+6*math.sin(math.radians(a))) for a in range(-135,136,6)]
        if direction<0:points=[(20-x,y) for x,y in points]
        line(*points)
        end=points[-1];previous=points[-3]
        vx,vy=end[0]-previous[0],end[1]-previous[1];length=math.hypot(vx,vy);vx/=length;vy/=length
        line((end[0]-vx*4-vy*3,end[1]-vy*4+vx*3),end,(end[0]-vx*4+vy*3,end[1]-vy*4-vx*3))
    elif name=='calculate':
        box(4,2,16,18);box(6,4,14,7)
        for x in (7,11,14):
            for y in (10,14):line((x,y),(x+.2,y))
    elif name in ('checkall','uncheckall'):
        box(3,3,17,17)
        if name=='checkall':line((6,10),(9,13),(14,7))
        else:line((6,10),(14,10))
    elif name=='link':
        box(2,7,10,13);box(10,7,18,13);line((7,10),(13,10))
    elif name=='folder':
        line((2,6),(2,3),(8,3),(10,6),(18,6),(18,17),(2,17),(2,6),(18,6))
    elif name=='close':
        box(3,2,15,18);line((7,7),(11,11));line((11,7),(7,11))
    elif name=='rename':
        box(2,3,12,17);line((7,13),(9,8),(15,2),(18,5),(12,11),(7,13));line((13,4),(16,7))
    elif name=='delete':
        line((4,5),(16,5));line((7,3),(13,3));line((5,6),(6,17),(14,17),(15,6));line((8,8),(8,14));line((12,8),(12,14))
    elif name=='exception':
        box(3,2,17,18);line((6,5),(14,5));line((6,9),(11,9));line((13,10),(13,16));line((10,13),(16,13))
    elif name in ('addsection','deletesection'):
        box(2,2,12,18);line((4,6),(10,6));line((4,10),(10,10));line((4,14),(10,14))
        line((14,12),(19,12))
        if name=='addsection':line((16.5,9),(16.5,15))
    elif name=='addrow':
        line((5,2),(14,2),(14,7));box(2,5,11,18)
        for y in (9,13):line((2,y),(11,y))
        line((16,10),(16,18));line((12,14),(20,14))
    elif name=='catalog':
        box(2,3,8,17);box(10,3,16,17);line((5,6),(5,13));line((13,6),(13,13))
    elif name=='save':
        box(3,2,17,18);box(6,2,13,7);box(6,11,14,17)
    elif name=='passports':
        line((2,7),(2,4),(7,4),(9,6),(18,6),(18,17),(2,17),(2,7));line((8,12),(11,15),(16,9))
    elif name=='deleterow':
        line((5,2),(14,2),(14,7));box(2,5,11,18)
        for y in (9,13):line((2,y),(11,y))
        line((12,14),(20,14))
    elif name=='sun':
        d.ellipse((6*scale,6*scale,14*scale,14*scale),outline=color,width=5)
        for a,b,c,e in [(10,1,10,4),(10,16,10,19),(1,10,4,10),(16,10,19,10),(3,3,5,5),(15,15,17,17),(3,17,5,15),(15,5,17,3)]:line((a,b),(c,e))
    elif name=='moon':
        d.ellipse((2*scale,2*scale,18*scale,18*scale),fill=color);d.ellipse((8*scale,-1*scale,22*scale,14*scale),fill=(0,0,0,0))
    elif name=='home':
        line((2,9),(10,3),(18,9));line((5,8),(5,17),(15,17),(15,8));line((8,17),(8,12),(12,12),(12,17))
    return ImageTk.PhotoImage(im.resize((18,18),Image.Resampling.LANCZOS),master=master)
