from app_paths import EXAMPLES_ROOT
from pathlib import Path
import tempfile,shutil,queue
from workspace_preview import Session
from project_analysis import saved_word_plan
source=next((EXAMPLES_ROOT/'КНС').rglob('*.docx'))
with tempfile.TemporaryDirectory() as td:
 file=Path(td)/source.name;shutil.copy2(source,file)
 def opened():
  s=Session(file,queue.Queue(),prepared=True);vals=None
  while True:
   _,k,v=s.events.get(timeout=60)
   if k=='error':raise AssertionError(v)
   if k=='fields':vals=v
   if k=='pdf':return s,vals
 def render(s,vals):
  s.tasks.put((vals,1))
  while True:
   _,k,v=s.events.get(timeout=60)
   if k=='error':raise AssertionError(v)
   if k=='pdf':return
 def stop(s):s.tasks.put(None);s.thread.join(15);assert not s.thread.is_alive()
 s,vals=opened();vals.update(actDate='',workStart='',notes='');render(s,vals);stop(s)
 assert saved_word_plan(file) is not None
 print('SAVED',saved_word_plan(file)['fields'].keys(),flush=True)
 s,vals=opened();print('REOPEN',s.analysis.get('prepared'),list(vals),flush=True)
 if 'actDate' not in vals:stop(s);raise AssertionError('date missing on reopen')
 assert vals['actDate']=='' and vals['workStart']=='' and 'notes' in vals
 vals.update(actDate='06.08.2027',workStart='05.08.2027',notes='Заполнено после повторного открытия');render(s,vals);stop(s)
 s,vals=opened();assert vals['actDate']=='06.08.2027' and vals['workStart']=='05.08.2027' and vals['notes']=='Заполнено после повторного открытия';stop(s)
print('PASS cleared dates/notes remain editable across reopening and can be filled later, including August date')
