$files='RegisterRows.ps1','WordFields.ps1','PreviewWorker.ps1','ReviewHighlight.ps1'
foreach($file in $files){$tokens=$null;$errors=$null;$null=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PWD $file),[ref]$tokens,[ref]$errors);if($errors){throw ($errors|Out-String)}}
