param([Parameter(Mandatory=$true)][string]$WorkFile,[string]$FieldMap,[string]$ActLayout,[string]$PreparedFile)
$ErrorActionPreference='Stop'
# Explicit UTF-8 on both sides of the local worker pipe.
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
function Send($object){[Console]::WriteLine((ConvertTo-Json -InputObject $object -Compress -Depth 6))}
function FormulaErrors{
 if($excel){GetFormulaErrors $doc}
}
function DisplayDate($iso,$sample){
 if(!$iso){return ''}
 $date=[datetime]::ParseExact($iso,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
 $m=[regex]::Match($sample,'(?<d>\d{1,2})(?<gap>[^\p{L}\d]*)(?<m>\d{1,2}|[а-яА-ЯёЁ]+)(?<gap2>[^\p{L}\d]*)(?<y>\d{4}|\d{2})(?!\d)')
 if(!$m.Success){throw "Не удалось определить запись даты в шаблоне: $sample"}
 $month=if($m.Groups['m'].Value -match '^\d+$'){$date.Month.ToString(('0'*$m.Groups['m'].Length))}else{@('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря')[$date.Month-1]}
 $day=$date.Day.ToString(('0'*$m.Groups['d'].Length))
 $year=if($m.Groups['y'].Length -eq 2){$date.ToString('yy')}else{$date.Year}
 return $sample.Substring(0,$m.Index)+$day+$m.Groups['gap'].Value+$month+$m.Groups['gap2'].Value+$year+$sample.Substring($m.Index+$m.Length)
}
function IsoDate($text){
 $m=[regex]::Match($text,'(\d{1,2})[^\p{L}\d]+([а-яё]+)[^\d]+(\d{4})')
 if(!$m.Success){return ''}
 $n=1+[array]::IndexOf(@('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'),$m.Groups[2].Value)
 if(!$n){return ''};return '{0}-{1:00}-{2:00}' -f $m.Groups[3].Value,$n,[int]$m.Groups[1].Value
}
. (Join-Path $PSScriptRoot 'ActFlow.ps1')
. (Join-Path $PSScriptRoot 'RegisterRows.ps1')
. (Join-Path $PSScriptRoot 'WordFields.ps1')
. (Join-Path $PSScriptRoot 'ReviewHighlight.ps1')
. (Join-Path $PSScriptRoot 'FormulaValidation.ps1')
$probeBook=$null;$pinned=$false;$app=$null;$doc=$null
try{
 $excel=[IO.Path]::GetExtension($WorkFile) -in '.xls','.xlsx'
 if($excel){$app=New-Object -ComObject Excel.Application;$app.EnableEvents=$false}else{$app=New-Object -ComObject Word.Application}
 $app.AutomationSecurity=3;$app.DisplayAlerts=0
 $fields=[ordered]@{};$original=@{};$bindings=@{}
 if($excel){
  $doc=$app.Workbooks.Open($WorkFile,0,$false);$sheet=$doc.Worksheets.Item(1)
  $layout=if($ActLayout){Get-Content -LiteralPath $ActLayout -Raw -Encoding UTF8|ConvertFrom-Json}
  $known=$null -ne $layout -and $null -ne $layout.fields.end -and @($layout.fields.end).Count -gt 0
  if($known){
   $map=[ordered]@{};foreach($prop in $layout.fields.psobject.Properties){$map[$prop.Name]=@($prop.Value)}
   foreach($k in $map.Keys){
    $bindings[$k]=@($map[$k])
    $parts=@(foreach($coord in $bindings[$k]){($sheet.Range($coord).Text).Trim()})
    for($i=0;($more=BoundCell (MoreName $k $i));$i++){$more.MergeArea.Borders.Item(9).LineStyle=1;$more.MergeArea.Borders.Item(9).Weight=2;$parts+=([string]$more.Text).Trim()}
    $v=($parts -join ' ').Trim()
    $original[$k]=$v
    if($k -in 'start','end','date'){$v=IsoDate $v}
    $fields[$k]=$v
   }
   $dateFormula='='+$bindings['end'][0]
  }
  # Only explicitly bound user fields are editable on unfamiliar forms.
  foreach($named in $doc.Names){if($named.Name -match '^ID_'){try{$cell=$named.RefersToRange.Cells.Item(1,1);if(!$cell.HasFormula){$bindings[$named.Name]=$cell;$fields[$named.Name]=[string]$cell.Text}}catch{}}}
 }else{
  $openPath=if($PreparedFile){$PreparedFile}else{$WorkFile}
  $doc=$app.Documents.Open($openPath,$false,$false,$false)
  foreach($bm in $doc.Bookmarks){if($bm.Name -like 'ID_*'){$fields[$bm.Name]=$bm.Range.Text}}
 }
 $special=@{}
 if($FieldMap){$spec=Get-Content -LiteralPath $FieldMap -Raw -Encoding UTF8|ConvertFrom-Json;foreach($prop in $spec.psobject.Properties){$special[$prop.Name]=$prop.Value;$fields[$prop.Name]=[string]$prop.Value.value}}
 $registerRepaired=$false
 if($excel -and $special.Keys -match '^row'){
  SetupRegisterPrint $sheet
  $registerRepaired=RepairDamagedRegister $sheet
  if($registerRepaired){
   $app.CalculateFull();$doc.Save()
   foreach($k in $special.Keys){
    if($special[$k].label -eq 'Страницы'){$fields[$k]=[string]$sheet.Range([string]$special[$k].dest).Text}
   }
  }
 }
 Send @{ready=$true;fields=$fields;registerRepaired=$registerRepaired}
 $cleanReady=$false
 $last=@{};foreach($k in $fields.Keys){$last[$k]=$fields[$k]}
 while($line=[Console]::ReadLine()){
  try{
   $req=$line|ConvertFrom-Json
   if($req.batch){
    $b=$req.batch;$cleanReady=$false;$deferRegisterSave=$true
    try{
     if($b.section){
      if(!$excel){throw 'Разделы доступны только в распознанном общем реестре Excel.'}
      $selected=EditRegisterSection ([int]$b.section) ([bool]$b.delete) ([string]$b.title)
     }else{
      $targets=@($b.rows | Where-Object {$null -ne $_});if(!$targets.Count){$targets=@([int]$b.row)}
      $targets=@($targets | ForEach-Object {[int]$_} | Sort-Object -Unique -Descending)
      # Validate the complete request before changing any rows.
      $valid=if($excel){@(GetRegisterRows $sheet (GetRegisterLayout $sheet))}else{@($special.Keys | Where-Object {$_ -match '^row\d+_'} | ForEach-Object {[int]($_.Split('_')[0].Substring(3))})}
      foreach($target in $targets){if($target -notin $valid){throw 'Выбрана устаревшая строка. Повторите выбор.'}}
      $selected=[int]$b.row
      if($b.delete){foreach($target in $targets){if($excel){RemoveRegisterPosition $target}else{AddWordRegisterPosition $target $true}}}
      else{
       $count=if($b.count){[int]$b.count}else{1};if($count -lt 1 -or $count -gt 500){throw 'Допустимо от 1 до 500 строк.'}
       $target=[int]$targets[-1]
       for($i=0;$i -lt $count;$i++){$selected=if($excel){AddRegisterPosition $target}else{AddWordRegisterPosition $target};$target=$selected}
      }
     }
    }finally{$deferRegisterSave=$false}
    if($excel){SetupRegisterPrint $sheet;$app.CalculateFull()}else{UpdateWordTotals}
    $doc.Save()
    Send @{ok=$true;row=$selected;fields=$fields;spec=$special};continue
   }
   if($req.delete){
    $cleanReady=$false
    if($excel){RemoveRegisterPosition ([int]$req.delete);Send @{ok=$true}}else{AddWordRegisterPosition ([int]$req.delete) $true;Send @{ok=$true;fields=$fields;spec=$special}};continue
   }
   if($req.insert){
    $cleanReady=$false
    if($excel){$inserted=AddRegisterPosition ([int]$req.insert);Send @{ok=$true;row=$inserted}}else{$newWord=AddWordRegisterPosition ([int]$req.insert);Send @{ok=$true;fields=$fields;spec=$special;row=$newWord}};continue
   }
   if($req.reload){
    $special=@{};$fields=[ordered]@{};$last=@{}
    foreach($prop in $req.reload.psobject.Properties){$special[$prop.Name]=$prop.Value;$fields[$prop.Name]=[string]$prop.Value.value;$last[$prop.Name]=$fields[$prop.Name]}
    Send @{fields=$fields};continue
   }
   foreach($prop in $req.values.psobject.Properties){
    $k=$prop.Name;$v=[string]$prop.Value;if(!$fields.Contains($k) -or $v -ceq $last[$k]){continue}
    $cleanReady=$false
    if($special.ContainsKey($k)){
     $entry=$special[$k]
     if($excel){
      $cell=$sheet.Range([string]$entry.dest)
      if($entry.kind -eq 'datecell' -and $v){$day=[datetime]::ParseExact($v,'dd.MM.yyyy',[Globalization.CultureInfo]::InvariantCulture);$cell.GetType().InvokeMember("Value2",[Reflection.BindingFlags]::SetProperty,$null,$cell,@($day.ToOADate()))|Out-Null}
      elseif($entry.kind -eq 'number' -and $v){$cell.GetType().InvokeMember("Value2",[Reflection.BindingFlags]::SetProperty,$null,$cell,@([double]::Parse($v)))|Out-Null}
      elseif($entry.label -eq 'Страницы' -and $v -match '^\d+-\d+$'){$cell.Value2="'"+$v} else{$cell.Value2=[string]$entry.prefix+$v}
     }elseif($entry.word){
      $display=$v
      if($k -in 'materials','attachments','schemes','project','hiddenWorks'){$display=[regex]::Replace($display,'(\b\d{2}\.\d{2}\.\d{4})(?!\d)(?!\s*г\.?)','$1 г.')}
      SetWordField $entry $display
     }else{
      $r=$doc.Paragraphs.Item([int]$entry.dest).Range.Duplicate
      $r.Start=$r.Start+([string]$entry.prefix).Length;$r.End=$r.End-1;$r.Text=$v
     }
     $last[$k]=$v;continue
    }
    if($excel){
     if($k -like 'ID_*'){$bindings[$k].Value2=$v}
     elseif($k -in 'start','end','date'){
      $cell=BoundCell (FieldName $k 0);if(!$cell){$cell=$sheet.Range($bindings[$k][0])};$sample=$original[$k]
      if(!$sample -or !(IsoDate $sample)){$sample='"01" января 2000г.'}
      if($k -eq 'date' -and $v -eq $req.values.end){$endCell=BoundCell (FieldName 'end' 0);$cell.Formula=if($endCell){'='+$endCell.Address(0,0)}else{$dateFormula}}
      else{$cell.Value2=(DisplayDate $v $sample)}
     }else{
      $display=$v
      if($k -in 'materials','attachments','schemes','project','hiddenWorks'){$display=[regex]::Replace($display,'(\b\d{2}\.\d{2}\.\d{4})(?!\d)(?!\s*г\.?)','$1 г.')}
      SetActText $k $display
     }
    }else{$r=$doc.Bookmarks.Item($k).Range;$r.Text=$v;[void]$doc.Bookmarks.Add($k,$r)}
    $last[$k]=$v
   }
   if($excel -and $known -and $original.materials -match 'к АО(СР|ОК).* от \d{2}\.\d{2}\.\d{4}' -and $req.values.materials -ceq $fields.materials){
    $referenceDate=if($req.values.date){DisplayDate $req.values.date '01.01.2000'}else{''}
    $materialCell=BoundCell (FieldName 'materials' 0);if(!$materialCell){$materialCell=$sheet.Range($bindings.materials[0])};$materialCell.Value2=[regex]::Replace($original.materials,'(?<= от )\d{2}\.\d{2}\.\d{4}',$referenceDate)
   }
   if(!$cleanReady -or !(Test-Path -LiteralPath ([string]$req.pdf))){
   if(!$excel){UpdateWordTotals}elseif($special.Keys -match '^row'){$app.CalculateFull()}else{$app.Calculate()}
   if(!$excel -and $PreparedFile){$format=if([IO.Path]::GetExtension($WorkFile) -eq '.doc'){0}else{16};$doc.SaveAs2($WorkFile,$format);$PreparedFile=''}else{$doc.Save()}
   if($excel){$doc.ExportAsFixedFormat(0,[string]$req.pdf)}else{$doc.ExportAsFixedFormat([string]$req.pdf,17)}
    $cleanReady=$true
   }
   # The clean preview is ready now. Let Tk display it before the more expensive
   # coloured review-copy export, without allowing review colours into the file.
   Send @{cleanReady=$true;formulaErrors=@(FormulaErrors)}
   $hasReview=ExportReviewPdf $req
   Send @{ok=$true;hasReview=$hasReview}
  }catch{Send @{error=$_.Exception.Message}}
 }
}catch{Send @{error=$_.Exception.Message}}
finally{if($probeBook){$probeBook.Close($false)};if($doc){$doc.Close($false)};if($app){$app.Quit()}}






