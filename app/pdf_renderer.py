"""Nonblocking front end to one isolated, persistent renderer process."""
import queue,threading,subprocess,pickle,sys
from pathlib import Path

class PDFRenderer:
 def __init__(self):
  self.jobs=queue.Queue();self.results=queue.Queue();self.generation=0;self.epoch=0;self.closed=False;self.process=None;self.render_count=0
  self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()
 def open(self,source,generation):
  self.generation=generation;self.jobs.put(dict(op='open',source=source if isinstance(source,bytes) else str(source),generation=generation))
 def page(self,generation,epoch,page,zoom,rotation):
  self.jobs.put(dict(op='page',generation=generation,epoch=epoch,page=page,zoom=zoom,rotation=rotation))
 def locate(self,generation,values):
  self.jobs.put(dict(op='locate',generation=generation,values=values))
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
    if job['generation']!=self.generation or job['op']=='page' and job['epoch']!=self.epoch:continue
    pickle.dump(job,p.stdin,protocol=5);p.stdin.flush();result=pickle.load(p.stdout)
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
