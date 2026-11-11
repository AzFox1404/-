function GetRegisterLayout($ws){
 $lastRow=$ws.UsedRange.Row+$ws.UsedRange.Rows.Count-1
 $lastColumn=$ws.UsedRange.Column+$ws.UsedRange.Columns.Count-1
 $general=([string]$ws.Range('A5').Text) -match 'РЕЕСТР ИСПОЛНИТЕЛЬНОЙ'
 $quality=([string]$ws.Range('B8').Text) -match 'материал'
 $scheme=([string]$ws.Range('B8').Text) -match 'Наименование документа' -and ([string]$ws.Range('C8').Text) -match '^Номер документа'
 if(!$general -and !$quality -and !$scheme){
  for($r=1;$r -le [math]::Min(30,$lastRow);$r++){
   $title=0;$ordinal=0;$count=0;$page=0
   for($c=1;$c -le $lastColumn;$c++){
    $v=([string]$ws.Cells.Item($r,$c).Text).ToLower()
    if($v -match '^наименование'){$title=$c}
    if($v -match '№\s*п\s*[./]\s*п'){$ordinal=$c}
    if($v -match '(лист|страниц)' -and $v -match '(кол|число)'){$count=$c}
    elseif($v -match '(лист|страниц)' -and $v -match '(порядков|сквоз|по порядку|по списку|№\s*страниц)'){$page=$c}
   }
   if(!$title -or $ordinal -ne 1 -or !$count -or !$page){continue}
   for($end=$r+1;$end -le $lastRow;$end++){
    if(([string]$ws.Cells.Item($end,$ordinal).Text).Trim() -match '^(Передал|Принял|Сдал|Сдача|Приемка|Приёмка)'){break}
   }
   if($end -gt $lastRow){break}
   $mode='start';$helperStart='';$helperEnd=''
   for($n=$r+1;$n -lt $end;$n++){
    $formula=[string]$ws.Cells.Item($n,$page).Formula
    if($formula -match '^=IF\(([A-Z]+)\d+=([A-Z]+)\d+,'){
     $mode='range';$helperStart=$Matches[1];$helperEnd=$Matches[2];break
    }
   }
   return @{general=$false;quality=$false;custom=$true;first=$r+1;bottom=$end-1;lastcol=$lastColumn;ordinal=$ordinal;count=$count;page=$page;mode=$mode;helperStart=$helperStart;helperEnd=$helperEnd}
  }
  throw 'Не распознана таблица реестра.'
 }
 $marker=if($general){$ws.UsedRange.Find('Передал')}else{$ws.UsedRange.Find('Всего страниц:')}
 if(!$marker){throw 'Не найдена граница таблицы реестра.'}
 return @{general=$general;quality=$quality;first=$(if($general){8}else{9});bottom=([int]$marker.Row-1);lastcol=$(if($scheme -and !$general){5}else{6})}
}
function GetRegisterRows($ws,$layout,[int]$forced=0){
 for($r=$layout.first;$r -le $layout.bottom;$r++){
  $cell=$ws.Cells.Item($r,1)
  # Section headings are merged horizontally. Displayed Text is unsuitable:
  # a real position may currently show #REF! or #### because of its format.
  if($cell.MergeArea.Columns.Count -gt 1){continue}
  if($layout.custom -and $r -ne $forced){
   $content=$ws.Application.WorksheetFunction.CountA($ws.Range($ws.Cells.Item($r,1),$ws.Cells.Item($r,$layout.lastcol)))
   if(!$content -and $cell.Borders.Item(9).LineStyle -eq -4142){continue}
  }
  $v=[string]$cell.Value2
  if(!$layout.general -or $r -eq $forced -or $cell.HasFormula -or $v -match '^\d+$' -or ([string]$ws.Cells.Item($r,2).Value2).Trim()){$r}
 }
}
function GetRegisterPageMode($ws,$rows){
 foreach($r in $rows){
  $cell=$ws.Cells.Item($r,6);$formula=[string]$cell.Formula
  if($formula -match '^=F\d+\+E(\d+)$'){if([int]$Matches[1] -eq $r){return 'end'}else{return 'start'}}
  if(([string]$cell.Value2) -match '^\d+\s*-\s*\d+$'){return 'range'}
  if($formula -match '&"-"&'){return 'range'}
  if($formula -match 'SUM\(E\d+:E(\d+)\)'){if([int]$Matches[1] -eq $r){return 'end'}else{return 'start'}}
 }
 return 'start'
}
function RepairRegisterNumbers($ws,[int]$forced=0,[string]$pageMode=''){
 $layout=GetRegisterLayout $ws;$rows=@(GetRegisterRows $ws $layout $forced)
 if(!$rows.Count){return}
 if($layout.custom){
  $previous=0;$ordinalPrevious=0;$scanned=$layout.first
  foreach($r in $rows){
   for($header=$scanned;$header -lt $r;$header++){
    $head=$ws.Cells.Item($header,$layout.ordinal);$text=([string]$head.Value2).Trim()
    if($head.MergeArea.Columns.Count -gt 1 -and $text -and $text -notmatch '^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения)'){$ordinalPrevious=0}
   }
   $scanned=$r+1
   $ordinal=$ws.Cells.Item($r,$layout.ordinal);$ordinal.NumberFormat='0'
   $ordinal.Formula=if($ordinalPrevious){'='+$ws.Cells.Item($ordinalPrevious,$layout.ordinal).Address(0,0)+'+1'}else{'=1'}
   $ordinalPrevious=$r
   $page=$ws.Cells.Item($r,$layout.page)
   $countCell=$ws.Cells.Item($r,$layout.count).Address(0,0)
   $firstCount=$ws.Cells.Item($rows[0],$layout.count).Address(0,0)
   $start=if($previous){'1+SUM('+$firstCount+':'+$ws.Cells.Item($previous,$layout.count).Address(0,0)+')'}else{'1'}
   $end='SUM('+$firstCount+':'+$countCell+')'
   if($layout.mode -eq 'range'){
    $ws.Range($layout.helperStart+$r).Formula='='+$start
    $ws.Range($layout.helperEnd+$r).Formula='='+$end
    $page.Formula='=IF('+ $countCell +'="","",IF('+ $countCell +'>1,('+ $start +')&"-"&('+ $end +'),'+ $start +'))'
   }else{$page.Formula='=IF('+$countCell+'="","",'+$start+')'}
   $previous=$r
  }
  return
 }
 if($layout.general -and !$pageMode){$pageMode=GetRegisterPageMode $ws $rows}
 $previous=0;$first=[int]$rows[0];$scanned=$layout.first
 foreach($r in $rows){
  if($layout.general){
   for($header=$scanned;$header -lt $r;$header++){
    $head=$ws.Cells.Item($header,1);$text=([string]$head.Value2).Trim()
    if($head.MergeArea.Columns.Count -gt 1 -and $text -and $text -notmatch '^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения)'){$previous=0}
   }
   $scanned=$r+1
  }
  $ordinal=$ws.Cells.Item($r,1);$ordinal.NumberFormat='0'
  $ordinal.Formula=if($previous){"=A$previous+1"}else{'=1'}

  $previous=$r
 }
 if($layout.general){[void](UpdateRegisterPages $ws $rows $pageMode)}
 if(!$layout.general){
  $letter=if($layout.quality){'F'}else{'E'};$total=$layout.bottom+1
  $ws.Range("$letter$total").Formula="=SUM(${letter}$first`:${letter}$($layout.bottom))"
 }
}
function UpdateRegisterPages($ws,$rows,[string]$pageMode=''){
 if(!$rows.Count){return $false}
 if(!$pageMode){$pageMode=GetRegisterPageMode $ws $rows}
 $first=[int]$rows[0];$previous=0;$changed=$false
 foreach($r in $rows){
   $page=$ws.Cells.Item($r,6)
   $start=if($previous){"1+SUM(E${first}:E$previous)"}else{'1'}
   $end="SUM(E${first}:E$r)"
   $expression=if($pageMode -eq 'end'){$end}elseif($pageMode -eq 'range'){"IF(E$r>1,($start)&`"-`"&($end),$start)"}else{$start}
   $formula="=IF(E$r=`"`",`"`",$expression)"
   if(([string]$page.Formula) -ne $formula -or $page.NumberFormat -ne '0'){$page.NumberFormat='0';$page.Formula=$formula;$changed=$true}
   $previous=$r
 }
 return $changed
}
function RepairDamagedRegister($ws){
 $layout=GetRegisterLayout $ws;$rows=@(GetRegisterRows $ws $layout);$needs=$false;$index=0
 if($layout.custom){
  foreach($r in $rows){
   $ordinal=$ws.Cells.Item($r,$layout.ordinal)
   $page=$ws.Cells.Item($r,$layout.page)
   if(!([string]$ordinal.Value2).Trim() -or ([string]$ordinal.Formula) -match '#REF!' -or ([string]$page.Formula) -match '#REF!'){
    RepairRegisterNumbers $ws
    return $true
   }
  }
  return $false
 }
 foreach($r in $rows){
  $index++;$a=$ws.Cells.Item($r,1)
  if(([string]$a.Formula) -match '#REF!' -or ([string]$a.Text) -match '^#' -or (!$layout.general -and ([string]$a.Value2) -ne [string]$index)){$needs=$true;break}
  if($layout.general -and ([string]$ws.Cells.Item($r,6).Formula) -match '#REF!'){$needs=$true;break}
 }
 if($needs){RepairRegisterNumbers $ws;return $true}
 if($layout.general){return (UpdateRegisterPages $ws $rows)}
 $letter=if($layout.quality){'F'}else{'E'};$total=$layout.bottom+1
 $formula="=SUM(${letter}$($layout.first):${letter}$($layout.bottom))"
 if(([string]$ws.Range("$letter$total").Formula) -ne $formula){$ws.Range("$letter$total").Formula=$formula;return $true}
 return $false
}
function SetupRegisterPrint($ws){
 $general=([string]$ws.Range('A5').Text) -match 'РЕЕСТР ИСПОЛНИТЕ'
 $old=$ws.UsedRange.Find('Всего позиций')
 if($old){
  $r=$old.Row
  if($general -and ([string]$ws.Range("B$r").Text) -eq 'Всего позиций'){
   [void]$ws.Range("A${r}:F${r}").ClearContents()
  }elseif(!$general -and ([string]$ws.Range("B$r").Text) -eq 'Всего позиций' -and ([string]$ws.Range("A$r").Formula) -match '^=COUNT\('){
   [void]$ws.Range("A${r}:B${r}").ClearContents()
  }
 }
 $ws.PageSetup.Zoom=$false;$ws.PageSetup.FitToPagesWide=1;$ws.PageSetup.FitToPagesTall=$false
}
function AddRegisterPosition([int]$row,[bool]$after=$false){
 $layout=GetRegisterLayout $sheet;$rows=@(GetRegisterRows $sheet $layout)
 if($row -notin $rows){throw 'Выберите строку позиции.'}
 $pageMode=if($layout.general){GetRegisterPageMode $sheet $rows}else{''}
 $atStart=$row -eq $rows[0]
 if($layout.general -and $row -gt $layout.first){$atStart=$atStart -or $sheet.Cells.Item($row-1,1).MergeArea.Columns.Count -gt 1}
 $new=if($atStart -and !$after){$row}else{$row+1}
 [void]$sheet.Rows.Item($new).Insert()
 $source=if($new -le $row){$row+1}else{$row}
 [void]$sheet.Rows.Item($source).Copy($sheet.Rows.Item($new))
 $sheet.Rows.Item($new).RowHeight=$sheet.Rows.Item($source).RowHeight
 for($col=1;$col -le $layout.lastcol;$col++){
  $cell=$sheet.Cells.Item($new,$col)
  if(!$cell.HasFormula){[void]$cell.ClearContents()}
 }
 RepairRegisterNumbers $sheet $new $pageMode
 if(!$deferRegisterSave){SetupRegisterPrint $sheet;$app.CalculateFull();$doc.Save()}
 return $new
}
function RemoveRegisterPosition([int]$row){
 $layout=GetRegisterLayout $sheet;$rows=@(GetRegisterRows $sheet $layout)
 if($row -notin $rows){throw 'Выберите строку позиции.'}
 $pageMode=if($layout.general){GetRegisterPageMode $sheet $rows}else{''}
 if($rows.Count -le 1){for($c=2;$c -le $layout.lastcol;$c++){$cell=$sheet.Cells.Item($row,$c);if(!$cell.HasFormula){[void]$cell.ClearContents()}}}
 else{[void]$sheet.Rows.Item($row).Delete()}
 RepairRegisterNumbers $sheet 0 $pageMode
 if(!$deferRegisterSave){SetupRegisterPrint $sheet;$app.CalculateFull();$doc.Save()}
}

function EditRegisterSection([int]$start,[bool]$delete,[string]$title){
 $layout=GetRegisterLayout $sheet
 if(!$layout.general -and !$layout.custom){throw 'Разделы поддерживаются только в общем реестре.'}
 $headers=@()
 for($r=$layout.first;$r -le $layout.bottom;$r++){
  $cell=$sheet.Cells.Item($r,1);$text=([string]$cell.Value2).Trim()
  if($cell.MergeArea.Columns.Count -gt 1 -and $text -and $text -notmatch '^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения)'){$headers+=$r}
 }
 if($start -notin $headers){throw 'Не подтверждена граница раздела.'}
 $next=@($headers | Where-Object {$_ -gt $start} | Select-Object -First 1)
 $end=if($next.Count){[int]$next[0]-1}else{$layout.bottom}
 # Leave the blank separator preceding the signatures outside the section.
 while($end -gt $start -and $sheet.Application.WorksheetFunction.CountA($sheet.Range($sheet.Cells.Item($end,1),$sheet.Cells.Item($end,$layout.lastcol))) -eq 0){$end--}
 $rows=@(GetRegisterRows $sheet $layout);$mode=GetRegisterPageMode $sheet $rows
 if($delete){
  if($headers.Count -lt 2){throw 'Нельзя удалить последний раздел.'}
  [void]$sheet.Rows.Item("${start}:${end}").Delete();$selected=$start
 }else{
  $title=$title.Trim()
  if(!$title){throw 'Введите название раздела.'}
  if($title -match '^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения|Передал|Принял)'){throw 'Это название обозначает группу документов или подпись. Введите название раздела.'}
  $at=$end+1;$length=$end-$start+1;$last=$at+$length-1
  [void]$sheet.Rows.Item("${at}:${last}").Insert()
  [void]$sheet.Rows.Item("${start}:${end}").Copy($sheet.Rows.Item("${at}:${last}"))
  $sheet.Cells.Item($at,1).Value2=$title
  foreach($r in $rows){
   if($r -le $start -or $r -gt $end){continue}
   $dest=$at+$r-$start
   for($c=2;$c -le $layout.lastcol;$c++){
    $cell=$sheet.Cells.Item($dest,$c)
    if(!$cell.HasFormula){[void]$cell.ClearContents()}
   }
  }
  $selected=$at+1
 }
 RepairRegisterNumbers $sheet 0 $mode;SetupRegisterPrint $sheet
 return $selected
}

