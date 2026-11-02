"""Persistent, incremental recovery journal; baseline copies stay local to a project."""
from pathlib import Path
import json,base64,shutil
class PersistentSpace:
 def __init__(self,path):self.name=str(path);Path(path).mkdir(parents=True,exist_ok=True)
 def cleanup(self):
  path=Path(self.name).resolve()
  if path.name!='.recovery':raise ValueError('Invalid recovery path')
  shutil.rmtree(path,ignore_errors=True)
def persist(j):
 data=dict(files=[str(x) for x in j.files],dirs=[str(x) for x in j.dirs],manifest=base64.b64encode(j.manifest).decode(),copies={str(k):str(v.relative_to(j.root)) for k,v in j.copies.items()},dirty=[str(x.relative_to(j.base)) for x in j.dirty],removed=[str(x.relative_to(j.base)) for x in j.removed],drafts=getattr(j,'drafts',{}),origins={str(k):str(v) for k,v in j.origins.items()},checkpoints={str(k):str(v.relative_to(j.root)) for k,v in j.checkpoints.items()},working={str(k):str(v.relative_to(j.root)) for k,v in j.working.items()},changed=[str(x.relative_to(j.base)) for x in j.changed],saved_names={str(k):str(v) for k,v in j.saved_names.items()})
 p=j.root/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(data,ensure_ascii=False),'utf-8');t.replace(p)
def load(j):
 p=j.root/'state.json'
 if not p.exists():j.drafts={};persist(j);return
 data=json.loads(p.read_text('utf-8'))
 def safe(v):
  rel=Path(v)
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('Invalid recovery entry')
  return rel
 j.files={safe(x) for x in data['files']};j.dirs={safe(x) for x in data['dirs']};j.manifest=base64.b64decode(data['manifest'])
 copies=data['copies'];j.copies={safe(k):j.root/safe(v) for k,v in copies.items()} if isinstance(copies,dict) else {safe(x):j.root/safe(x) for x in copies}
 j.dirty={j.base/safe(x) for x in data['dirty']};j.removed={j.base/safe(x) for x in data['removed']};j.drafts=data.get('drafts',{})
 j.origins={safe(k):safe(v) for k,v in data.get('origins',{}).items()};j.checkpoints={safe(k):j.root/safe(v) for k,v in data.get('checkpoints',{}).items()};j.working={safe(k):j.root/safe(v) for k,v in data.get('working',{}).items()};j.changed={j.base/safe(x) for x in data.get('changed',[])}
 j.saved_names={safe(k):safe(v) for k,v in data.get('saved_names',{}).items()}
def archive(j):
 from datetime import datetime
 import uuid
 if not j.dirty_project():return
 dest=j.project/'.backups'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5]);dest.mkdir(parents=True)
 (dest/'project.json').write_bytes(j.manifest)
 for rel,source in j.copies.items():
  target=dest/'Документы'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
