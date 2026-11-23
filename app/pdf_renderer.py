"""Nonblocking front end to one isolated, persistent renderer process."""
import queue,threading,subprocess,pickle,sys,time,tempfile
from pathlib import Path

class PDFRenderer:
 def __init__(self):
  self.jobs=queue.Queue();self.results=queue.Queue();self.generation=0;self.epoch=0;self.closed=False;self.process=None;self.render_count=0
  self.viewport=0;self.active_tile=None
  from collections import deque
  self.timings=deque(maxlen=128)
  self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()
 def open(self,source,generation,page_range=None):
  self.generation=generation;self.jobs.put(dict(op='open',source=source if isinstance(source,bytes) else str(source),generation=generation,page_range=page_range))
 def set_epoch(self,epoch):
  from collections import deque
  self.epoch=epoch
  for q in (self.jobs,self.results):
   with q.mutex:
    q.queue=deque(j for j in q.queue if j is None or j.get('op') not in ('page','tile') or j.get('overview') or j.get('epoch')==epoch)
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
  diagnostics=None
  def stop():
   nonlocal diagnostics
   code=None;detail=''
   p=self.process
   if p:
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=2)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
    code=p.returncode
    for stream in (p.stdin,p.stdout):
     if stream:
      try:stream.close()
      except OSError:pass  # A dead child can leave an unflushable stdin buffer.
    self.process=None
   if diagnostics:
    diagnostics.seek(0,2);size=diagnostics.tell();diagnostics.seek(max(0,size-8192))
    detail=diagnostics.read().decode('utf-8',errors='replace').strip()
    diagnostics.close();diagnostics=None
   return code,detail
  try:
   while not self.closed:
    job=self.jobs.get()
    if job is None:break
    if job['generation']!=self.generation or job['op']=='page' and not job.get('overview') and job['epoch']!=self.epoch:continue
    if self.process is None and job['op']!='open':continue
    try:
     if self.process is None:
      diagnostics=tempfile.TemporaryFile()
      self.process=subprocess.Popen([sys.executable,'-u',str(Path(__file__).with_name('pdf_render_worker.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=diagnostics,creationflags=subprocess.CREATE_NO_WINDOW)
     p=self.process
     if self.closed:break
     self.active_tile=(job['page'],job['zoom'],job['rotation'],*job['tile']) if 'tile' in job else None
     started=time.perf_counter()
     pickle.dump(job,p.stdin,protocol=5);p.stdin.flush();result=pickle.load(p.stdout);self.active_tile=None
     if 'render_ms' in result:
      self.timings.append(dict(op=result['op'],render_ms=result['render_ms'],roundtrip_ms=round((time.perf_counter()-started)*1000,2)))
     if job['op']=='page':self.render_count+=1
     if job['generation']==self.generation and (job['op']!='page' or job.get('overview') or job['epoch']==self.epoch):self.results.put(result)
    except (OSError,EOFError,pickle.UnpicklingError) as exc:
     code,detail=stop();self.active_tile=None
     if "No module named 'pymupdf'" in detail:
      message='Не установлен PyMuPDF в среде запуска приложения. Установите зависимости из requirements.txt и перезапустите приложение.'
     else:
      reason=detail.splitlines()[-1] if detail else str(exc)
      message=f'Процесс предпросмотра PDF завершился (код {code}). {reason}'
     if not self.closed:self.results.put(dict(op='error',generation=job['generation'],error=message))
  finally:
   stop()
