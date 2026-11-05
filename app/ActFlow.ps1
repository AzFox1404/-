# Stable references survive Excel row insertion and are saved in the working copy.
function FieldName($key,$n){return "BID_field_${key}_$n"}
function MoreName($key,$n){return "BID_more_${key}_$n"}
function BoundCell($name){try{return ,$doc.Names.Item($name).RefersToRange.Cells.Item(1,1)}catch{return $null}}
function BindCell($name,$cell){
 $ref="='"+$sheet.Name.Replace("'","''")+"'!"+$cell.Address()
 [void]$doc.Names.Add($name,$ref,$false)
}
function PinLayout {
 foreach($key in $map.Keys){
  for($i=0;$i -lt $bindings[$key].Count;$i++){
   $name=FieldName $key $i
   if(!(BoundCell $name)){BindCell $name ($sheet.Range($bindings[$key][$i]))}
  }
 }
}
function NextSegment($text,$source,$width){
 if(!$text){return ''}
 if(!$script:probeBook){$script:probeBook=$app.Workbooks.Add()}
 $probe=$script:probeBook.Worksheets.Item(1).Range('A1')
 $probe.Font.Name=$source.Font.Name;$probe.Font.Size=$source.Font.Size
 $probe.Font.Bold=$source.Font.Bold;$probe.Font.Italic=$source.Font.Italic
 $probe.WrapText=$false;$probe.ShrinkToFit=$false
 $probe.Orientation=0;$probe.IndentLevel=0
 $words=[regex]::Matches($text,'\S+');if(!$words.Count){return ''}
 $lo=0;$hi=$words.Count
 while($lo -lt $hi){
  $mid=[int][math]::Ceiling(($lo+$hi)/2);$word=$words[$mid-1];$try=$text.Substring(0,$word.Index+$word.Length)
  if($try.Length -gt 200){$hi=$mid-1;continue}
  $probe.NumberFormat='@';$probe.Value2=$try;[void]$probe.EntireColumn.AutoFit()
  if($probe.Width -le $width-2){$lo=$mid}else{$hi=$mid-1}
 }
 if(!$lo){
  # A long identifier cannot be split at a space; split by glyph only as a last resort.
  $low=0;$high=[math]::Min(200,$words[0].Length)
  while($low -lt $high){$mid=[int][math]::Ceiling(($low+$high)/2);$probe.Value2=$text.Substring(0,$mid);[void]$probe.EntireColumn.AutoFit();if($probe.Width -le $width-2){$low=$mid}else{$high=$mid-1}}
  return $text.Substring(0,[math]::Max(1,$low))
 }
 $end=$words[$lo-1];return $text.Substring(0,$end.Index+$end.Length)
}
function SmallCaptionRow($row){
 $cells=$sheet.Range("B${row}:M${row}")
 foreach($c in $cells.Cells){if([string]$c.Text -and $c.Font.Size -le 9){return $true}}
 return $false
}
function NewContinuation($source,$row,$name){
 [void]$sheet.Rows.Item($row).Insert()
 $line=$sheet.Range("B${row}:M${row}");$line.UnMerge();$line.Merge()
 $line.RowHeight=[math]::Max([double]$source.RowHeight,[double]$source.Font.Size*1.45)
 $line.Font.Name=$source.Font.Name;$line.Font.Size=$source.Font.Size
 $line.Font.Bold=$source.Font.Bold;$line.Font.Italic=$source.Font.Italic
 $line.Font.Color=$source.Font.Color;$line.Font.Underline=-4142
 $line.Interior.ColorIndex=$source.Interior.ColorIndex
 $line.HorizontalAlignment=$source.HorizontalAlignment;$line.VerticalAlignment=$source.VerticalAlignment
 $line.NumberFormat=$source.NumberFormat;$line.WrapText=$false;$line.ShrinkToFit=$false
 foreach($edge in 7,8,9,10){$old=$source.MergeArea.Borders.Item($edge);$new=$line.Borders.Item($edge);$new.LineStyle=$old.LineStyle;if($old.LineStyle -ne -4142){$new.Weight=$old.Weight;$new.Color=$old.Color}}
 # The template may draw its rule as font underline rather than a border.
 $line.Borders.Item(9).LineStyle=1;$line.Borders.Item(9).Weight=2;$line.Borders.Item(9).Color=0
 BindCell $name $line.Cells.Item(1,1)
 return ,$line.Cells.Item(1,1)
}
function SetActText($key,$value){

 # Recreate owned continuation rows at the correct position, before any caption.
 for($n=0;($old=BoundCell (MoreName $key $n));$n++){
  $doc.Names.Item((MoreName $key $n)).Delete();[void]$old.EntireRow.Delete()
 }
 $text=[regex]::Replace($value.Trim(),'[\r\n\t]+',' ')
 $source=$null
 for($i=0;$i -lt $bindings[$key].Count;$i++){
  $source=BoundCell (FieldName $key $i)
  if(!$source){$source=$sheet.Range($bindings[$key][$i])}
  if(!$source -or ([string]$source.Text).TrimStart().StartsWith('(') -and $source.Font.Size -le 9){throw "Нет безопасного поля для $key"}
  $source.MergeArea.WrapText=$false;$source.MergeArea.ShrinkToFit=$false
  $source.MergeArea.VerticalAlignment=-4107
  $source.RowHeight=[math]::Max([double]$source.RowHeight,[double]$source.Font.Size*1.5+2)
  $part=NextSegment $text $source $source.MergeArea.Width
  $source.Font.Underline=-4142;$source.MergeArea.Borders.Item(9).LineStyle=1;$source.MergeArea.Borders.Item(9).Weight=2
  $source.Value2=$part;$text=$text.Substring($part.Length).TrimStart()
 }
 $row=$source.Row+1
 if($text){
  for($n=0;$n -lt $bindings[$key].Count;$n++){
   $original=BoundCell (FieldName $key $n)
   if(!$original){$original=$sheet.Range($bindings[$key][$n])}
   $original.Font.Underline=-4142;$original.MergeArea.Borders.Item(9).LineStyle=1
  }
 }
 $i=0
 while($text){
  $name=MoreName $key $i;$line=BoundCell $name
  if(!$line){if(!$script:pinned){PinLayout;$script:pinned=$true};$line=NewContinuation $source $row $name}
  $part=NextSegment $text $source $line.MergeArea.Width;$line.Value2=$part
  $text=$text.Substring($part.Length).TrimStart();$row=$line.Row+1;$i++
 }
 while($line=BoundCell (MoreName $key $i)){
  $doc.Names.Item((MoreName $key $i)).Delete();[void]$line.EntireRow.Delete();$i++
 }
 # Excel can move the preceding bottom border when the next row is inserted.
 # Reapply the rules after all structural changes have finished.
 for($n=0;($line=BoundCell (MoreName $key $n));$n++){
  $line.Font.Underline=-4142
  $line.MergeArea.Borders.Item(9).LineStyle=1
  $line.MergeArea.Borders.Item(9).Weight=2
  $line.MergeArea.Borders.Item(9).Color=0
 }
 if($i -gt 0){
  for($n=0;$n -lt $bindings[$key].Count;$n++){
   $line=BoundCell (FieldName $key $n)
   $line.Font.Underline=-4142;$line.MergeArea.Borders.Item(9).LineStyle=1
  }
 }
}

