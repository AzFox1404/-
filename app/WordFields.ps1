function SetWordField($entry,[string]$value){
 $parts=@($entry.segments)
 $remaining=$value
 $date=$null
 if($entry.worddate -and $value){$date=[datetime]::ParseExact($value,'dd.MM.yyyy',[Globalization.CultureInfo]::InvariantCulture)}
 for($i=0;$i -lt $parts.Count;$i++){
  $part=$parts[$i];$name=[string]$part.bookmark
  if(!$doc.Bookmarks.Exists($name)){throw "Не найдена привязка поля: $name. Повторно откройте документ."}
  if($date){
   $sample=[string]$part.sample
   if($parts.Count -eq 1){if(!$sample.Trim()){$sample=if($entry.sample){[string]$entry.sample}else{'01.01.2000'}};$replacement=DisplayDate $date.ToString('yyyy-MM-dd') $sample}
   else{
    $replacement=$sample
    if($sample.Trim() -match '^\d{1,2}$'){$replacement=$date.Day.ToString(('0'*$sample.Trim().Length))}
    elseif($sample.Trim() -match '^\d{4}$'){$replacement=[string]$date.Year}
    else{
     $month=@('января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря')[$date.Month-1]
     $replacement=[regex]::Replace($replacement,'января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря',$month)
     $replacement=[regex]::Replace($replacement,'\d{4}',[string]$date.Year)
    }
   }
  }elseif($i -eq $parts.Count-1){$replacement=$remaining}
  else{
   $capacity=[int]$part.capacity
   if($remaining.Length -le $capacity){$replacement=$remaining;$remaining=''}else{
    $cut=$remaining.LastIndexOf(' ',[Math]::Min($capacity,$remaining.Length-1))
    if($cut -le 0){$cut=[Math]::Min($capacity,$remaining.Length)}
    $replacement=$remaining.Substring(0,$cut);$remaining=$remaining.Substring($cut).TrimStart()
   }
  }
  $range=$doc.Bookmarks.Item($name).Range.Duplicate
  $range.Text=([string]$replacement).Replace("`n","`v")
  [void]$doc.Bookmarks.Add($name,$range)
 }
}
function AddWordRegisterPosition([int]$row,[bool]$delete=$false,[bool]$after=$false){
 $template=@($special.Keys | Where-Object {$_ -like "row${row}_*"})
 if(!$template){throw 'Выберите строку реестра.'}
 $tableIds=@($special.Keys | Where-Object {$_ -match '^row\d+_'} | ForEach-Object {$special[$_].wordTable} | Sort-Object -Unique)
 if($tableIds.Count -gt 1){throw 'В документе несколько таблиц реестров. Сначала требуется отдельная привязка выбранной таблицы.'}
 $entry=$special[$template[0]];$table=$doc.Tables.Item([int]$entry.wordTable)
 $labels=@{};$dateFlags=@{};$samples=@{}
 foreach($key in $template){$item=$special[$key];$c=[int]$item.wordColumn;$labels[$c]=$item.label;$dateFlags[$c]=$item.worddate;$samples[$c]=$item.sample}
 if($delete){
  $positions=0;for($r=2;$r -le $table.Rows.Count;$r++){if(([string]$table.Rows.Item($r).Cells.Item(1).Range.Text).Trim([char]13,[char]7) -match '^\d+$'){$positions++}}
  if($positions -le 1){for($c=2;$c -le $table.Rows.Item($row).Cells.Count;$c++){$cell=$table.Rows.Item($row).Cells.Item($c);$calculated=$false;foreach($field in $cell.Range.Fields){if(([string]$field.Code.Text) -match '^\s*='){$calculated=$true}};if(!$calculated){$cell.Range.Text=''}}}else{$table.Rows.Item($row).Delete()}
 }else{
 $first=(@($special.Keys|Where-Object {$_ -match '^row\d+_'}|ForEach-Object {[int]($_.Split('_')[0].Substring(3))}|Sort-Object)[0])
 $new=if($row -eq $first -and !$after){$row}else{$row+1}
 if($new -le $table.Rows.Count){$null=$table.Rows.Add($table.Rows.Item($new))}else{$null=$table.Rows.Add()}
 $sourceRow=if($new -le $row){$row+1}else{$row}
 $added=$table.Rows.Item($new)
 for($c=1;$c -le $added.Cells.Count;$c++){
  $cell=$added.Cells.Item($c);$cell.Range.Text=''
  $source=$table.Rows.Item($sourceRow).Cells.Item($c).Range
  $cell.Range.Font.Name=$source.Font.Name;$cell.Range.Font.Size=$source.Font.Size;$cell.Range.Font.Bold=$source.Font.Bold;$cell.Range.Font.Italic=$source.Font.Italic
 }
 }
 foreach($key in @($special.Keys)){
  if($key -match '^row\d+_'){
   foreach($segment in $special[$key].segments){if($doc.Bookmarks.Exists([string]$segment.bookmark)){$doc.Bookmarks.Item([string]$segment.bookmark).Delete()}}
   $special.Remove($key);$fields.Remove($key);$last.Remove($key)
  }
 }
 $ordinal=0
 for($r=2;$r -le $table.Rows.Count;$r++){
  $first=$table.Rows.Item($r).Cells.Item(1).Range.Text.Trim([char]13,[char]7)
  if(($delete -or $r -ne $new) -and $first -notmatch '^\d+$'){continue}
  $ordinal++;$table.Rows.Item($r).Cells.Item(1).Range.Text=[string]$ordinal
  foreach($c in $labels.Keys){
   $range=$table.Rows.Item($r).Cells.Item([int]$c).Range.Duplicate;$range.End=$range.End-1
   if(([string]$range.Text).EndsWith("`r")){$range.End=$range.End-1}
   $name="BID_row_${r}_${c}";[void]$doc.Bookmarks.Add($name,$range)
   $key="row${r}_${c}";$value=([string]$range.Text).Trim()
   $item=@{dest=$name;segments=@(@{bookmark=$name;sample=$value;capacity=[Math]::Max(1,$value.Length)});value=$value;label=$labels[$c];kind=$(if($dateFlags[$c]){'datecell'}else{'text'});word=$true;worddate=$dateFlags[$c];sample=$(if($value){$value}else{$samples[$c]});wordTable=[int]$entry.wordTable;wordColumn=$c}
   if($item.worddate){$item.segments[0].sample=$item.sample}
   $special[$key]=$item;$fields[$key]=$value;$last[$key]=$value
  }
 }
 foreach($formula in $table.Range.Fields){if(([string]$formula.Code.Text) -match '^\s*=\s*(SUM|COUNT)\s*\('){[void]$formula.Update()}}
 if(!$deferRegisterSave){$doc.Save()}
 if(!$delete){return $new}
}

function UpdateWordTotals(){
 for($i=1;$i -le $doc.Tables.Count;$i++){
  $formulas=$doc.Tables.Item($i).Range.Fields
  for($j=1;$j -le $formulas.Count;$j++){
   $formula=$formulas.Item($j)
   if(([string]$formula.Code.Text) -match '^\s*=\s*(SUM|COUNT)\s*\('){[void]$formula.Update()}
  }
 }
}
