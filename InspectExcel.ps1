param([string]$Source,[string]$Target)
$ErrorActionPreference='Stop';$app=$null;$book=$null
try{$app=New-Object -ComObject Excel.Application;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3;$book=$app.Workbooks.Open($Source,0,$true);$book.SaveAs($Target,51)}finally{if($book){$book.Close($false)};if($app){$app.Quit()}}
