"""Compare old/current wheel interaction on the same generated A0, no Office."""
import importlib.util,tempfile,time,tkinter as tk,os,statistics
from pathlib import Path
from types import SimpleNamespace
import pymupdf as fitz
import studio
from pdf_page_preview import PagePreview

def pump(root,seconds):
    end=time.perf_counter()+seconds
    while time.perf_counter()<end:root.update();time.sleep(.002)

def wait(root,condition,seconds=20):
    end=time.perf_counter()+seconds
    while not condition():
        if time.perf_counter()>end:raise AssertionError('timeout')
        pump(root,.005)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=p/'projects';studio.LIB=p/'library';studio.SAMPLES=p/'absent/sample'
    source=p/'drawing.pdf';doc=fitz.open();page=doc.new_page(width=2384,height=3370)
    for y in range(10,3300,15):
        page.draw_line((10,y),(2300,y));page.insert_text((20,y+10),'SMALL TEXT 0123456789 '*10,fontsize=7)
    doc.save(source);doc.close()
    sample=os.environ.get('BUREAU_ID_ZOOM_SAMPLE')
    if sample:source.write_bytes(Path(sample).read_bytes())
    original=source.read_bytes()
    versions=[]
    baseline=os.environ.get('BUREAU_ID_ZOOM_BASELINE')
    if baseline:
        spec=importlib.util.spec_from_file_location('old_view',baseline);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        versions.append(('before',module.PagePreview))
    versions.append(('after',PagePreview))
    root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    results={}
    for name,cls in versions:
        win=tk.Toplevel(root);win.geometry('850x650');v=cls(win,app);v.pack(fill='both',expand=True)
        pump(root,.1);v.show(source,0)
        wait(root,lambda:bool(v.tiles.visible or v.images) and not v.tiles.pending)
        v.set_zoom(100);wait(root,lambda:bool(v.tiles.visible or v.images) and not v.tiles.pending)
        x,y=300,260;cy=v.canvas.canvasy(y);cx=v.canvas.canvasx(x)
        top,w,h,_=v.pages[0];anchor=((cx-8)/w,(cy-top)/h)
        first=[None];started=time.perf_counter();before=v.renderer.render_count
        for i in range(10):
            v.zoom_at(SimpleNamespace(x=x,y=y,delta=120 if i<6 else -120))
            pump(root,max(0,started+(i+1)*.028-time.perf_counter()))
            if first[0] is None and v.zoom!=100:first[0]=(time.perf_counter()-started)*1000
            if name=='after':
                assert v._interactive_zoom
                assert not v.tiles.pending,'exact rendering must wait until wheel settles'
                assert v.canvas.find_withtag('pdf-overview'),'visible draft missing'
        if name=='after':
            # No intermediate native exact renders; the already-active old job may finish.
            assert v.renderer.render_count<=before+1
            assert v.renderer.jobs.qsize()<6
            assert first[0] is not None,'feedback must appear while the wheel is moving'
        wait(root,lambda:v._zoom_job is None and v.zoom==120)
        if first[0] is None:first[0]=(time.perf_counter()-started)*1000
        wait(root,lambda:bool(v.images) or bool(v.tiles.required) and v.tiles.required.issubset(v.tiles.visible))
        sharp_ms=round((time.perf_counter()-started)*1000,1)
        top,w,h,_=v.pages[0]
        now=((v.canvas.canvasx(x)-8)/w,(v.canvas.canvasy(y)-top)/h)
        assert abs(now[0]-anchor[0])*w<5 and abs(now[1]-anchor[1])*h<5,(anchor,now)
        results[name]=dict(first_ms=round(first[0],1),sharp_ms=sharp_ms)
        print('METRIC',name,'native render/roundtrip median ms:',{k:round(statistics.median(t[k] for t in v.renderer.timings),2) for k in ('render_ms','roundtrip_ms')})
        if name=='after':
            assert v.tiles.bytes<=48*1024*1024
            v.zoom_at(SimpleNamespace(x=x,y=y,delta=120));pump(root,.02)
        win.destroy();pump(root,.05)
    if baseline:assert results['after']['first_ms']<results['before']['first_ms'],results
    assert source.read_bytes()==original and not errors,errors
    root.destroy()
    print('METRIC first wheel feedback ms on '+('local sample copy' if sample else 'generated A0')+':',results)
    print('PASS immediate draft, deferred exact tiles, latest scale, cursor anchor, bounded queue/cache, close during zoom and unchanged source')
