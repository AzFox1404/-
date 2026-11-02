param([string]$Source,[string]$Target)
$ErrorActionPreference='Stop'
$app=$null;$doc=$null
try{
 $app=New-Object -ComObject Word.Application;$app.Visible=$false;$app.DisplayAlerts=0;$app.AutomationSecurity=3
 $doc=$app.Documents.Open($Source,$false,$true,$false)
 $doc.SaveAs2($Target,16)
}finally{if($doc){$doc.Close(0)};if($app){$app.Quit()}}
