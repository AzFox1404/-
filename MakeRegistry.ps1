param([string]$File,[string]$Data,[string]$Pdf)
$ErrorActionPreference='Stop'
$app=$null;$book=$null
try{
 $payload=Get-Content -LiteralPath $Data -Raw -Encoding UTF8 | ConvertFrom-Json
 $app=New-Object -ComObject Excel.Application;$app.DisplayAlerts=$false;$app.AutomationSecurity=3;$app.EnableEvents=$false
 $book=$app.Workbooks.Open($File,0,$false);$s=$book.Worksheets.Item(1)
 if($s.Range('A5').Text -notmatch 'РЕЕСТР ИСПОЛНИТЕЛЬНОЙ'){throw 'Выберите образец общего реестра с заголовком в A5.'}
 $footer=$s.UsedRange.Find('Передал')
 if(!$footer){throw 'Не найдена строка «Передал» в общем реестре.'}
 $last=$footer.Row-1
 $sty=$book.Worksheets.Add();$s.Rows.Item(10).Copy($sty.Rows.Item(1))
 [void]$s.Rows.Item("8:$last").Delete()
 $rows=@($payload.entries);$n=$rows.Count+1
 if($n){[void]$s.Rows.Item("8:$($n+7)").Insert()}
 $r=8
 foreach($entry in $rows){
  $sty.Rows.Item(1).Copy($s.Rows.Item($r));$s.Range("A${r}:F${r}").ClearContents()|Out-Null
  $s.Range("A$r").Formula="=ROW()-7";$s.Range("B$r").Value2=[string]$entry.title
  $s.Range("C$r").NumberFormat='@';$s.Range("C$r").Value2=[string]$entry.number
  if($entry.date){$s.Range("D$r").NumberFormat='dd.mm.yyyy';$s.Range("D$r").Value2=[string]$entry.date}
  $s.Range("E$r").Formula="="+[string]$entry.count;$s.Range("F$r").NumberFormat='@';$s.Range("F$r").Value2=[string]$entry.span
  $s.Range("B$r").WrapText=$true;[void]$s.Rows.Item($r).AutoFit();$r++
 }
 # Leave one blank line between the last document and the handover block.
 if($payload.address){$s.Range('B3').Value2=[string]$payload.address}
 $sty.Delete();$s.PageSetup.Zoom=$false;$s.PageSetup.FitToPagesWide=1;$s.PageSetup.FitToPagesTall=$false
 $end=$s.UsedRange.Find('Принял').Row+1;$s.PageSetup.PrintArea="A1:F$end"
 $s.Activate();$book.Save();$book.ExportAsFixedFormat(0,$Pdf)
}finally{if($book){$book.Close($false)};if($app){$app.Quit()}}
