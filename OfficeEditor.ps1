param([string]$Source, [switch]$Check, [switch]$Choose)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class OfficePosition {
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after,int x,int y,int w,int height,uint flags);
}
"@
[Windows.Forms.Application]::EnableVisualStyles()
$base=Join-Path $PSScriptRoot 'Рабочие копии'
if(!$Source -and !$Check -and !$Choose){
 $sample=Join-Path (Split-Path $PSScriptRoot) 'ИД здание 1 - 18х48\1. КМ\1. Колонны\АОСР №КМ-1 Монтаж колонн.xlsx'
 if(Test-Path $sample){$Source=$sample}
}
if(!$Source){
 $dlg=New-Object Windows.Forms.OpenFileDialog
 $dlg.Title='Выберите документ или сохранённую рабочую копию'
 $dlg.Filter='Документы Word и Excel|*.doc;*.docx;*.xls;*.xlsx'
 if(Test-Path $base){$dlg.InitialDirectory=$base}
 if($dlg.ShowDialog() -ne 'OK'){return}
 $Source=$dlg.FileName
}
$Source=(Resolve-Path -LiteralPath $Source).Path
$ext=[IO.Path]::GetExtension($Source).ToLowerInvariant()
if($ext -notin '.doc','.docx','.xls','.xlsx'){throw 'Выберите документ Word или Excel.'}
$excel=$ext -in '.xlsx','.xls'
New-Item -Type Directory -Path $base -Force | Out-Null
$base=(Resolve-Path $base).Path
if($Source.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase) -and !$Check){$path=$Source}
else {
 $folder=Join-Path $base ([Guid]::NewGuid().ToString('N').Substring(0,10))
 New-Item -Type Directory -Path $folder | Out-Null
 $path=Join-Path $folder ([IO.Path]::GetFileName($Source))
 Copy-Item -LiteralPath $Source -Destination $path
 (Get-Item -LiteralPath $path).IsReadOnly=$false
}
$mapPath=$path+'.fields.json'
$fields=@{}
if(Test-Path -LiteralPath $mapPath){$m=Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8 | ConvertFrom-Json;foreach($p in $m.psobject.properties){$fields[$p.Name]=[string]$p.Value}}
function SaveMap {ConvertTo-Json -InputObject $fields | Set-Content -LiteralPath $mapPath -Encoding UTF8}
$app=$null;$doc=$null
try {
 $prog=if($excel){'Excel.Application'}else{'Word.Application'}
 $app=New-Object -ComObject $prog
 $app.AutomationSecurity=3
 if($excel){$app.EnableEvents=$false;$doc=$app.Workbooks.Open($path,0,$false)}
 else{$doc=$app.Documents.Open($path,$false,$false,$false)}
 if($doc.ReadOnly){throw 'Рабочая копия открылась только для чтения. Закройте другой экземпляр документа.'}
 if($Check){Write-Output ('Открыта рабочая копия: '+$doc.Name);return}
 $app.Visible=$true
 $area=[Windows.Forms.Screen]::PrimaryScreen.WorkingArea
 $width=[int]($area.Width*0.31)
 $form=New-Object Windows.Forms.Form
 $form.Text='Бюро ИД · Поля документа';$form.StartPosition='Manual'
 $form.SetBounds($area.Left,$area.Top,$width,$area.Height)
 $form.BackColor=[Drawing.ColorTranslator]::FromHtml('#FAF5F1')
 $form.Font=New-Object Drawing.Font('Segoe UI',10)
 function ArrangeEditor {
  if($excel){$app.WindowState=-4143;$h=$app.Hwnd}else{$app.WindowState=0;$h=$doc.ActiveWindow.Hwnd}
  [void][OfficePosition]::SetWindowPos([IntPtr]$h,[IntPtr]::Zero,($area.Left+$width),$area.Top,($area.Width-$width),$area.Height,0x14)
 }
 ArrangeEditor
 $panel=New-Object Windows.Forms.FlowLayoutPanel
 $panel.Dock='Fill';$panel.FlowDirection='TopDown';$panel.WrapContents=$false;$panel.AutoScroll=$true;$panel.Padding=New-Object Windows.Forms.Padding(14)
 $form.Controls.Add($panel)
 function Control($kind,$label,$height){$c=New-Object ('Windows.Forms.'+$kind);$c.Text=$label;$c.Width=$width-60;$c.Height=$height;$panel.Controls.Add($c);return $c}
 function Action($label,[scriptblock]$handler){$b=Control Button $label 34;$b.Add_Click($handler)}
 $title=Control Label 'Редактор документа' 28
 $title.Font=New-Object Drawing.Font('Segoe UI',14,[Drawing.FontStyle]::Bold)
 [void](Control Label ([IO.Path]::GetFileName($path)) 44)
 [void](Control Label 'Поля формы' 23)
 $list=Control ListBox '' 104
 foreach($key in ($fields.Keys|Sort-Object)){[void]$list.Items.Add($key)}
 [void](Control Label 'Название поля' 22)
 $name=Control TextBox '' 26
 [void](Control Label 'Значение' 22)
 $value=Control TextBox '' 68;$value.Multiline=$true
 function Notify($msg){[void][Windows.Forms.MessageBox]::Show($form,[string]$msg,'Бюро ИД')}
 function Target($id){if($excel){return ,$doc.Names.Item($id).RefersToRange}else{return ,$doc.Bookmarks.Item($id).Range}}
 $list.Add_SelectedIndexChanged({try{if($null -eq $list.SelectedItem){return};$k=[string]$list.SelectedItem;$name.Text=$k;$r=Target $fields[$k];if($excel){$r.Worksheet.Activate();$r.Select();$value.Text=[string]$r.Cells.Item(1,1).Text}else{$r.Select();$value.Text=$r.Text}}catch{Notify $_.Exception.Message}})
 Action 'Добавить поле из выделения' {try{
  $k=$name.Text.Trim();if(!$k -or $fields.ContainsKey($k)){throw 'Введите новое уникальное название поля.'}
  $id='ID_'+[guid]::NewGuid().ToString('N')
  if($excel){$r=$app.Selection;if($r.Worksheet.Parent.FullName -ne $doc.FullName){throw 'Выберите ячейку рабочей копии.'};$r=$r.Cells.Item(1,1).MergeArea.Cells.Item(1,1);[void]$doc.Names.Add($id,$r);$doc.Save()}
  else{if($app.ActiveDocument.FullName -ne $doc.FullName){throw 'Выберите текст рабочей копии.'};$r=$app.Selection.Range;if($r.Text -match '[\r\x07]'){throw 'Выделите текст поля внутри абзаца, без конца строки или ячейки.'};[void]$doc.Bookmarks.Add($id,$r);$doc.Save()}
  $fields[$k]=$id;SaveMap;[void]$list.Items.Add($k);$list.SelectedItem=$k
 }catch{Notify $_.Exception.Message}}
 Action 'Записать значение в документ' {try{
  $k=[string]$list.SelectedItem;if(!$k){throw 'Выберите поле.'};$r=Target $fields[$k]
  if($excel){if($r.HasFormula){throw 'Выбрана ячейка с формулой. Измените её непосредственно в Excel.'};$r.Value2=$value.Text}
  else{$r.Text=$value.Text;[void]$doc.Bookmarks.Add($fields[$k],$r)}
  $doc.Save()
 }catch{Notify $_.Exception.Message}}
 Action 'Снять привязку поля' {try{
  $k=[string]$list.SelectedItem;if(!$k){return};if($excel){$doc.Names.Item($fields[$k]).Delete()}else{$doc.Bookmarks.Item($fields[$k]).Delete()}
  $doc.Save();$fields.Remove($k);SaveMap;$list.Items.Remove($k);$name.Clear();$value.Clear()
 }catch{Notify $_.Exception.Message}}
 Action 'Открыть другой документ' {Start-Process powershell.exe -WindowStyle Normal -ArgumentList ('-NoProfile -STA -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'OfficeEditor.ps1')+'" -Choose')}
 Action 'Сохранить рабочую копию' {try{$doc.Save();Notify $path}catch{Notify $_.Exception.Message}}
 Action 'Расположить редактор справа' {try{ArrangeEditor}catch{Notify $_.Exception.Message}}
 [void](Control Label 'Шрифт, размер, цвет, заливку и строки меняйте на ленте самого документа. Привязку можно снять, сохранив текст.' 96)
 $form.Add_FormClosing({param($sender,$e) try{if($doc.Saved -eq $false){$doc.Save()}}catch{if([Windows.Forms.MessageBox]::Show('Не удалось сохранить рабочую копию. Закрыть панель?', 'Бюро ИД','YesNo') -ne 'Yes'){$e.Cancel=$true}}})
 [void]$form.ShowDialog()
}finally{
 if($doc){try{$doc.Close($false)}catch{}}
 if($app){try{if($excel){if($app.Workbooks.Count -eq 0){$app.Quit()}}elseif($app.Documents.Count -eq 0){$app.Quit()}}catch{}}
}
