import ast,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    sources=sorted(ROOT.glob('*.py'))+sorted((ROOT/'tools').glob('*.py'))
    for path in sources:ast.parse(path.read_text('utf-8-sig'),filename=str(path))
    assets=list((ROOT/'data').glob('*.json'))+list((ROOT/'docs').glob('*.json'))
    for path in assets:json.loads(path.read_text('utf-8-sig'))
    required=['workspace_preview.py','studio.py','app_paths.py','PreviewWorker.ps1','ReviewHighlight.ps1','pdf_render_worker.py','data/act_anchors.json','vendor/tkdnd-win-x64/LICENSE','vendor/tkdnd-win-x64/libtkdnd2.10.3.dll']
    for path in required:
        if not (ROOT/path).is_file():raise SystemExit('Missing resource: '+path)
    if sys.platform=='win32':
        script='$ErrorActionPreference="Stop";Get-ChildItem -LiteralPath . -Filter *.ps1 | ForEach-Object {$t=$null;$e=$null;$null=[System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e);if($e){throw ($e|Out-String)}}'
        subprocess.run(['powershell.exe','-NoProfile','-Command',script],cwd=ROOT,check=True,capture_output=True)
    print(f'PASS: {len(sources)} Python files, {len(assets)} JSON resources, runtime assets and PowerShell syntax; no GUI/Office/OCR started')
if __name__=='__main__':main()
