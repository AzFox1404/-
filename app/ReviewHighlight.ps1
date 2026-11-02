# Preview colours are applied to an expendable document copy, never the saved file.
function ExcelReviewRanges($book,$ws,[string]$key){
 if($special.ContainsKey($key)){return ,$ws.Range([string]$special[$key].dest).MergeArea}
 if($key -like 'ID_*'){try{return ,$book.Names.Item($key).RefersToRange.MergeArea}catch{}}
 if($bindings.ContainsKey($key)){
  for($i=0;$i -lt @($bindings[$key]).Count;$i++){
   $cell=$null
   try{$cell=$book.Names.Item((FieldName $key $i)).RefersToRange}catch{}
   if(!$cell){try{$cell=$ws.Range([string]$bindings[$key][$i])}catch{}}
   if($cell){,$cell.MergeArea}
  }
  for($i=0;$i -lt 100;$i++){
   try{$cell=$book.Names.Item((MoreName $key $i)).RefersToRange}catch{break}
   ,$cell.MergeArea
  }
 }
}
function WordReviewRanges($copy,[string]$key){
 if($special.ContainsKey($key)){
  $entry=$special[$key]
  if($entry.word){foreach($segment in $entry.segments){if($copy.Bookmarks.Exists([string]$segment.bookmark)){,$copy.Bookmarks.Item([string]$segment.bookmark).Range}}}
  else{$r=$copy.Paragraphs.Item([int]$entry.dest).Range.Duplicate;$r.Start+=([string]$entry.prefix).Length;$r.End--;,$r}
 }elseif($copy.Bookmarks.Exists($key)){,$copy.Bookmarks.Item($key).Range}
}
function ExportReviewPdf($request){
 $keys=@($request.changedKeys);$active=[string]$request.activeKey;$row=[int]$request.activeRow
 if((!$keys.Count -and !$active -and !$row -and !$request.structuralReview) -or !$request.reviewPdf){return $false}
 $extension=[IO.Path]::GetExtension($WorkFile)
 $temp=Join-Path ([IO.Path]::GetDirectoryName([string]$request.reviewPdf)) ('review-copy'+$extension)
 $copy=$null
 try{
  if($excel){
   $doc.SaveCopyAs($temp);$copy=$app.Workbooks.Open($temp,0,$false);$ws=$copy.Worksheets.Item(1);$ws.Activate();$ws.PageSetup.BlackAndWhite=$false
   if($row -gt 0){$layout=GetRegisterLayout $ws;$ws.Range("A${row}:$([char](64+$layout.lastcol))${row}").Interior.Color=65535}
   elseif($active){foreach($range in @(ExcelReviewRanges $copy $ws $active)){$range.Interior.Color=65535}}
   foreach($key in $keys){foreach($range in @(ExcelReviewRanges $copy $ws ([string]$key))){$range.Font.Color=255;try{$range.Dependents.Font.Color=255}catch{}}}
   if($request.structuralReview){
    $layout=GetRegisterLayout $ws
    if(!$layout.general){$letter=if($layout.quality){'F'}else{'E'};$ws.Range("$letter$($layout.bottom+1)").Font.Color=255}
   }
   $copy.ExportAsFixedFormat(0,[string]$request.reviewPdf)
  }else{
   [IO.File]::Copy($WorkFile,$temp,$true);$copy=$app.Documents.Open($temp,$false,$false,$false)
   if($row -gt 0){
    $entry=@($special.Keys|Where-Object {$_ -like "row${row}_*"}|ForEach-Object {$special[$_]})|Select-Object -First 1
    if($entry -and $entry.wordTable){$copy.Tables.Item([int]$entry.wordTable).Rows.Item($row).Shading.BackgroundPatternColor=65535}
   }elseif($active){foreach($range in @(WordReviewRanges $copy $active)){$range.Shading.BackgroundPatternColor=65535}}
   foreach($key in $keys){foreach($range in @(WordReviewRanges $copy ([string]$key))){$range.Font.Color=255}}
   if($request.structuralReview){foreach($table in $copy.Tables){foreach($formula in $table.Range.Fields){if(([string]$formula.Code.Text) -match '^\s*=\s*(SUM|COUNT)\s*\('){$formula.Result.Font.Color=255}}}}
   $copy.ExportAsFixedFormat([string]$request.reviewPdf,17)
  }
  return $true
 }finally{
  if($copy){$copy.Close($false)}
  if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Force}
 }
}
