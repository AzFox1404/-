from pathlib import Path
import json,subprocess,shutil,tempfile
pairs=json.loads(Path('review/word-visual/pairs.json').read_text('utf-8'))
for i,pair in enumerate(pairs):
 if '--changed' in __import__('sys').argv and i not in (1,2,4):continue
 for role in ('source','prepared'):
  with tempfile.TemporaryDirectory() as td:
   source=Path(td)/'sample.docx';shutil.copyfile(pair[role],source)
   pdf=Path(td)/'sample.pdf';worker=__import__('app_paths').APP_DIR/'PreviewWorker.ps1'
   proc=subprocess.Popen(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(worker),'-WorkFile',str(source)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
   ready=json.loads(proc.stdout.readline().lstrip('\ufeff'));assert 'error' not in ready,ready
   proc.stdin.write(json.dumps(dict(values={},pdf=str(pdf)))+'\n');proc.stdin.flush()
   response=json.loads(proc.stdout.readline().lstrip('\ufeff'));assert response.get('ok'),response
   proc.stdin.close();proc.wait(timeout=15)
   shutil.copyfile(pdf,Path(pair['directory'])/(role+'.pdf'));print(i,role,flush=True)
