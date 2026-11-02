import ast,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    sources=[p for folder in ('app','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))]
    for path in sources:ast.parse(path.read_text('utf-8-sig'),filename=str(path))
    assets=list((ROOT/'data').glob('*.json'))+list((ROOT/'docs').glob('*.json'))
    for path in assets:json.loads(path.read_text('utf-8-sig'))
    required=['Бюро ИД.cmd','app/workspace_preview.py','app/studio.py','app/app_paths.py','app/PreviewWorker.ps1','app/ReviewHighlight.ps1','app/FormulaValidation.ps1','app/fast_preview.py','app/final_pdf_cache.py','app/pdf_render_worker.py','data/act_anchors.json','vendor/tkdnd-win-x64/LICENSE','vendor/tkdnd-win-x64/libtkdnd2.10.3.dll']
    for path in required:
        if not (ROOT/path).is_file():raise SystemExit('Missing resource: '+path)
    if sys.platform=='win32':
        script='$ErrorActionPreference="Stop";Get-ChildItem -LiteralPath . -Filter *.ps1 | ForEach-Object {$t=$null;$e=$null;$null=[System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e);if($e){throw ($e|Out-String)}}'
        subprocess.run(['powershell.exe','-NoProfile','-Command',script],cwd=ROOT/'app',check=True,capture_output=True)
    print(f'PASS: {len(sources)} Python files, {len(assets)} JSON resources, runtime assets and PowerShell syntax; no GUI/Office/OCR started')
if __name__=='__main__':main()
