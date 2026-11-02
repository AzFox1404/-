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
 data=dict(files=[str(x) for x in j.files],dirs=[str(x) for x in j.dirs],manifest=base64.b64encode(j.manifest).decode(),copies=[str(x) for x in j.copies],dirty=[str(x.relative_to(j.base)) for x in j.dirty],removed=[str(x.relative_to(j.base)) for x in j.removed],drafts=getattr(j,'drafts',{}))
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
 j.copies={safe(x):j.root/safe(x) for x in data['copies']};j.dirty={j.base/safe(x) for x in data['dirty']};j.removed={j.base/safe(x) for x in data['removed']};j.drafts=data.get('drafts',{})
def archive(j):
 from datetime import datetime
 import uuid
 if not j.dirty_project():return
 dest=j.project/'.backups'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5]);dest.mkdir(parents=True)
 (dest/'project.json').write_bytes(j.manifest)
 for rel,source in j.copies.items():
  target=dest/'Документы'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
