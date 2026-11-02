"""Canonical staged snapshot + verified connector-commit adoption, no credentials.

GitHub network calls are made by the agent's authenticated connector, not here.
"""
import argparse,base64,datetime as dt,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.git'/'codex-sync'
REPO='AzFox1404/-'
PRIVATE={'Рабочая папка ИД','Рабочие копии','Пример выгрузки','.local_notes','.project-local.json','ПРОМПТ_РАЗРАБОТКИ.md','ПРАВИЛА_ПРОЕКТА.md','ПРАВИЛА_WORD.md'}
DOCUMENTS={'.pdf','.doc','.docx','.xls','.xlsx','.png','.jpg','.jpeg','.dwg','.zip','.7z'}
def git(*args,input=None):
    return subprocess.run(['git',*args],cwd=ROOT,input=input,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout

def export():
    STATE.mkdir(parents=True,exist_ok=True);files=[]
    for entry in git('ls-files','--stage','-z').split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,sha,stage=meta.decode().split();path=name.decode('utf-8')
        if stage!='0':raise RuntimeError('Resolve index conflicts first: '+path)
        parts=Path(path).parts
        if parts[0] in PRIVATE or '.recovery' in parts or '.backups' in parts or Path(path).suffix.lower() in DOCUMENTS or Path(path).name.startswith('.env') and Path(path).name!='.env.example':
            raise RuntimeError('Private/generated document must not be published: '+path)
        data=git('cat-file','blob',sha)
        try:
            if b'\0' in data:raise UnicodeError()
            content=data.decode('utf-8');encoding='utf-8'
        except UnicodeError:content=base64.b64encode(data).decode();encoding='base64'
        files.append(dict(path=path,mode=mode,sha=sha,encoding=encoding,content=content))
    bundle=dict(repository=REPO,branch='main',tree=git('write-tree').decode().strip(),files=files)
    path=STATE/'bundle.json';path.write_text(json.dumps(bundle,ensure_ascii=False),'utf-8')
    print(json.dumps({'file':str(path),'files':len(files),'tree':bundle['tree'],'binary':sum(f['encoding']=='base64' for f in files)}))

def identity(person):
    date=dt.datetime.fromisoformat(person['date'].replace('Z','+00:00'));offset=date.strftime('%z') or '+0000'
    return f"{person['name']} <{person['email']}> {int(date.timestamp())} {offset}"

def commit_bytes(meta,message):
    parents=meta.get('parents') or [{'sha':meta['parent']}]
    head=f"tree {meta['tree']['sha'] if isinstance(meta['tree'],dict) else meta['tree']}\n"
    head+=''.join('parent '+(p['sha'] if isinstance(p,dict) else p)+'\n' for p in parents)
    head+='author '+identity(meta['author'])+'\ncommitter '+identity(meta['committer'])+'\n'
    return (head+'\n'+message).encode('utf-8')

def adopt(path):
    envelope=json.loads(Path(path).read_text('utf-8-sig'));sha=envelope['sha'];variants=envelope.get('candidate_metadata') or [envelope]
    data=None;chosen=None
    for meta in variants:
        for message in dict.fromkeys((meta['message'],meta['message']+'\n',meta['message'].rstrip('\n')+'\n')):
            raw=commit_bytes(meta,message)
            if hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==sha:data=raw;chosen=meta;break
        if data is not None:break
    if data is None:raise RuntimeError('Remote commit bytes not verified; no local refs changed')
    tree=chosen['tree']['sha'] if isinstance(chosen['tree'],dict) else chosen['tree']
    if git('write-tree').decode().strip()!=tree:raise RuntimeError('Index differs from the published tree')
    git('diff','--quiet')
    if git('hash-object','-t','commit','-w','--stdin',input=data).decode().strip()!=sha:raise RuntimeError('Object hash mismatch')
    parents=chosen.get('parents') or [{'sha':chosen['parent']}]
    boundary=False
    for parent in parents:
        name=parent['sha'] if isinstance(parent,dict) else parent
        try:git('cat-file','-e',name+'^{commit}')
        except subprocess.CalledProcessError:boundary=True
    if boundary:
        shallow=ROOT/'.git/shallow';items=set(shallow.read_text().splitlines()) if shallow.exists() else set();items.add(sha);shallow.write_text('\n'.join(sorted(items))+'\n','ascii')
    git('update-ref','refs/heads/main',sha);git('symbolic-ref','HEAD','refs/heads/main');git('update-ref','refs/remotes/origin/main',sha)
    git('config','branch.main.remote','origin');git('config','branch.main.merge','refs/heads/main')
    STATE.mkdir(exist_ok=True);(STATE/'state.json').write_text(json.dumps({'repository':REPO,'branch':'main','published_sha':sha,'tree':tree,'mode':'authenticated-connector'},indent=2)+'\n','utf-8')
    print(json.dumps({'sha':sha,'tree':tree,'status':'local main and origin/main adopted after SHA verification'}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['export','adopt']);parser.add_argument('metadata',nargs='?');args=parser.parse_args()
    if args.command=='export':export()
    elif args.metadata:adopt(args.metadata)
    else:parser.error('adopt requires a remote-commit JSON file')
if __name__=='__main__':main()
