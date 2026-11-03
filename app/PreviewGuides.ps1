function GetPreviewGuides {
 if(!$excel){return @{kind='word'}}
 try{
  $ps=$sheet.PageSetup
  if(@($doc.Worksheets | Where-Object {$_.Visible -eq -1}).Count -gt 1 -or $ps.PrintHeadings){return @{kind='excel';unsupported=$true}}
  if($ps.PrintTitleRows -or $ps.PrintTitleColumns -or $sheet.VPageBreaks.Count -gt 0 -or $ps.CenterVertically -or (!$ps.Zoom -and $ps.FitToPagesTall)){return @{kind='excel';unsupported=$true;reason=@($ps.PrintTitleRows,$ps.PrintTitleColumns,$sheet.VPageBreaks.Count,$ps.CenterVertically,$ps.Zoom,$ps.FitToPagesTall)}}
  $range=$sheet.UsedRange
  if($ps.PrintArea){$range=$sheet.Range($ps.PrintArea)}else{
   $range=$sheet.Range($sheet.Cells.Item(1,1),$sheet.Cells.Item($range.Row+$range.Rows.Count-1,$range.Column+$range.Columns.Count-1))
  }
  if($range.Areas.Count -ne 1 -or $range.Rows.Count -gt 2000 -or $range.Columns.Count -gt 200){return @{kind='excel';unsupported=$true;reason='Unsupported range'}}
  $cols=@();$rows=@();$breaks=@()
  foreach($c in $range.Columns){$cols+=,@{name=($c.Cells.Item(1,1).Address(0,0) -replace '\d','');start=([double]$c.Left-[double]$range.Left);size=[double]$c.Width}}
  foreach($r in $range.Rows){$rows+=,@{name=[string]$r.Row;start=([double]$r.Top-[double]$range.Top);size=[double]$r.Height}}
  foreach($b in $sheet.HPageBreaks){$breaks+=([int]$b.Location.Row)}
  return @{kind='excel';cols=$cols;rows=$rows;breaks=$breaks;width=[double]$range.Width;left=[double]$ps.LeftMargin;right=[double]$ps.RightMargin;top=[double]$ps.TopMargin;zoom=$ps.Zoom;center=[bool]$ps.CenterHorizontally}
 }catch{return @{kind='excel';unsupported=$true;reason=$_.Exception.Message}}
}
