param([string]$Source,[string]$Cell,[string]$Field)
$ErrorActionPreference='Stop';$app=$null;$book=$null
try{$app=New-Object -ComObject Excel.Application;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3;$book=$app.Workbooks.Open($Source,0,$false);$range=$book.Worksheets.Item(1).Range($Cell);[void]$book.Names.Add($Field,("='"+$book.Worksheets.Item(1).Name.Replace("'","''")+"'!"+$range.Address($true,$true,1,$false)));$book.Save()}finally{if($book){$book.Close($false)};if($app){$app.Quit()}}
