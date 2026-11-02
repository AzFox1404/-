param([string]$General,[string]$Quality)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\RegisterRows.ps1')
$app=New-Object -ComObject Excel.Application;$app.DisplayAlerts=$false;$app.EnableEvents=$false
try{
 foreach($file in @($General,$Quality)){
  $doc=$app.Workbooks.Open($file,0,$false);$sheet=$doc.Worksheets.Item(1)
  try{
   $layout=GetRegisterLayout $sheet;$initial=@(GetRegisterRows $sheet $layout);$r=$initial[7]
   # Simulate files damaged by the old delete path and inherited date formats.
   $sheet.Range("A$r").Formula='=#REF!+1';$sheet.Range("A$r").NumberFormat='dd.mm.yyyy'
   if($layout.general){$sheet.Range("F$r").Formula='=#REF!+E'+$r}
   $expected=$initial.Count
   foreach($op in @('delete','insert','insert','delete','delete','insert')){
    $layout=GetRegisterLayout $sheet;$rows=@(GetRegisterRows $sheet $layout)
    $target=$rows[6]
    if($op -eq 'delete'){RemoveRegisterPosition $target;$expected--}else{AddRegisterPosition $target;$expected++}
    $layout=GetRegisterLayout $sheet;$rows=@(GetRegisterRows $sheet $layout)
    if($rows.Count -ne $expected){throw "Position count $($rows.Count) != $expected"}
    $i=0;$pages=0.0;$checked=$layout.first
    foreach($row in $rows){
     if($layout.general){for($head=$checked;$head -lt $row;$head++){if(([string]$sheet.Cells.Item($head,1).Value2) -in @('Конструкции железобетонные','Конструкции металлические','Архитектурные решения')){$i=0}};$checked=$row+1}
     $i++;$a=$sheet.Range("A$row")
     if($a.Value2 -ne $i -or $a.NumberFormat -ne '0' -or ([string]$a.Text) -match '#'){throw "Broken ordinal at A$row : $($a.Formula) / $($a.Text)"}
     if($layout.general){
      $leaves=$sheet.Range("E$row").Value2
      if($null -ne $leaves -and [string]$leaves -ne ''){$pages+=[double]$leaves;if($sheet.Range("F$row").Value2 -ne $pages){throw "Broken pages F$row : $($sheet.Range("F$row").Text) != $pages"}}
      if(([string]$sheet.Range("F$row").Formula) -match '#REF!'){throw "Stale page reference F$row"}
     }
    }
    if(!$layout.general){
     $total=$layout.bottom+1;$sum=0.0;foreach($row in $rows){$sum += [double]$sheet.Range("F$row").Value2}
     if($sheet.Range("F$total").Value2 -ne $sum){throw 'Wrong quality page total'}
    }
   }
   $doc.Save()
   Write-Output "PASS $file : six alternating edits; all $expected ordinals; no reference errors; correct pages/totals"
  }finally{$doc.Close($false)}
 }
}finally{$app.Quit()}
