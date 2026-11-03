"""Nonblocking front end to one isolated, persistent renderer process."""
import queue,threading,subprocess,pickle,sys
from pathlib import Path

class PDFRenderer:
 def __init__(self):
  self.jobs=queue.Queue();self.results=queue.Queue();self.generation=0;self.epoch=0;self.closed=False;self.process=None;self.render_count=0
  self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()
  self.viewport=0;self.active_tile=None
 def open(self,source,generation):
  self.generation=generation;self.jobs.put(dict(op='open',source=source if isinstance(source,bytes) else str(source),generation=generation))
 def page(self,generation,epoch,page,zoom,rotation):
  self.jobs.put(dict(op='page',generation=generation,epoch=epoch,page=page,zoom=zoom,rotation=rotation))
 def locate(self,generation,values):
  self.jobs.put(dict(op='locate',generation=generation,values=values))
 def tile(self,generation,epoch,page,zoom,rotation,rect,viewport,overview=False,text=False):
  self.jobs.put(dict(op='page',generation=generation,epoch=epoch,page=page,zoom=zoom,rotation=rotation,tile=rect,viewport=viewport,overview=overview,text=text))
 def set_viewport(self,serial,pages,wanted=None):
  self.viewport=serial
  with self.jobs.mutex:
   from collections import deque
   self.jobs.queue=deque(j for j in self.jobs.queue if j is None or 'tile' not in j and not j.get('overview') or 'tile' in j and (wanted is not None and (j['page'],j['zoom'],j['rotation'],*j['tile']) in wanted or wanted is None and j['viewport']==serial) or j.get('overview') and j['page'] in pages)
   pending={(j['page'],j['zoom'],j['rotation'],*j['tile']) for j in self.jobs.queue if j and 'tile' in j}
   if self.active_tile and wanted is not None and self.active_tile in wanted:pending.add(self.active_tile)
   return pending
 def close(self):
  self.closed=True;self.jobs.put(None)
  p=self.process
  if p and p.poll() is None:
   try:p.terminate()
   except OSError:pass
 def work(self):
  try:
   p=subprocess.Popen([sys.executable,'-u',str(Path(__file__).with_name('pdf_render_worker.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
   self.process=p
   if self.closed:p.terminate();return
   while not self.closed:
    job=self.jobs.get()
    if job is None:break
    if job['generation']!=self.generation or job['op']=='page' and not job.get('overview') and job['epoch']!=self.epoch:continue
    self.active_tile=(job['page'],job['zoom'],job['rotation'],*job['tile']) if 'tile' in job else None
    pickle.dump(job,p.stdin,protocol=5);p.stdin.flush();result=pickle.load(p.stdout);self.active_tile=None
    if job['op']=='page':self.render_count+=1
    if job['generation']==self.generation:self.results.put(result)
  except (OSError,EOFError,BrokenPipeError) as exc:
   if not self.closed:self.results.put(dict(op='error',generation=self.generation,error='Просмотр PDF: '+str(exc)))
  finally:
   if self.process:
    for stream in (self.process.stdin,self.process.stdout):
     if stream:stream.close()
    if self.process.poll() is None:self.process.terminate()
    self.process.wait()
