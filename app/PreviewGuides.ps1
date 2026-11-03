function GetPreviewGuides {
 if(!$excel){return @{kind='word'}}
 try{
  $ps=$sheet.PageSetup
  if(@($doc.Worksheets | Where-Object {$_.Visible -eq -1}).Count -gt 1 -or $ps.PrintHeadings){return @{kind='excel';unsupported=$true}}
  if($ps.PrintTitleColumns -or $ps.CenterVertically -or (!$ps.Zoom -and $ps.FitToPagesTall)){return @{kind='excel';unsupported=$true}}
  $range=$sheet.UsedRange
  if($ps.PrintArea){$range=$sheet.Range($ps.PrintArea)}else{
   $range=$sheet.Range($sheet.Cells.Item(1,1),$sheet.Cells.Item($range.Row+$range.Rows.Count-1,$range.Column+$range.Columns.Count-1))
  }
  if($range.Areas.Count -ne 1 -or $range.Rows.Count -gt 2000 -or $range.Columns.Count -gt 200){return @{kind='excel';unsupported=$true;reason='Unsupported range'}}
  foreach($b in $sheet.VPageBreaks){if($b.Location.Column -gt $range.Column -and $b.Location.Column -le $range.Column+$range.Columns.Count-1){return @{kind='excel';unsupported=$true}}}
  $cols=@();$rows=@();$breaks=@();$titles=@();$anchors=@()
  if($ps.PrintTitleRows -match '\$?(\d+):\$?(\d+)'){$titles=@([int]$Matches[1]..[int]$Matches[2])}
  foreach($c in $range.Columns){$cols+=,@{name=($c.Cells.Item(1,1).Address(0,0) -replace '\d','');start=([double]$c.Left-[double]$range.Left);size=[double]$c.Width}}
  foreach($r in $range.Rows){$rows+=,@{name=[string]$r.Row;start=([double]$r.Top-[double]$range.Top);size=[double]$r.Height}}
  foreach($r in $range.Rows){
   if($anchors.Count -ge 120){break}
   foreach($col in @(2,3,4)){
    $cell=$sheet.Cells.Item($r.Row,$col);$text=([string]$cell.Text).Trim();$size=$cell.Font.Size
    if($text.Length -ge 3 -and $text.Length -le 60 -and $size -is [double] -and !$cell.ShrinkToFit){$anchors+=,@{text=$text;size=[double]$size;bottom=([double]$cell.Top+[double]$cell.Height-[double]$range.Top);height=[double]$cell.Height;align=[int]$cell.VerticalAlignment}}
   }
  }
  foreach($b in $sheet.HPageBreaks){$r=[int]$b.Location.Row;if($r -gt $range.Row -and $r -le $range.Row+$range.Rows.Count-1){$breaks+=$r}}
  return @{kind='excel';anchors=$anchors;cols=$cols;rows=$rows;breaks=@($breaks|Sort-Object -Unique);titles=$titles;width=[double]$range.Width;left=[double]$ps.LeftMargin;right=[double]$ps.RightMargin;top=[double]$ps.TopMargin;zoom=$ps.Zoom;center=[bool]$ps.CenterHorizontally}
 }catch{return @{kind='excel';unsupported=$true;reason=$_.Exception.Message}}
}
