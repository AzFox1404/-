Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$ErrorActionPreference='Stop'
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} |Select-Object -First 1
function Await($op,$type){$t=$method.MakeGenericMethod($type).Invoke($null,@($op));$t.GetAwaiter().GetResult()}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ru'))
while($line=[Console]::ReadLine()){
 try{
 if(!$engine){throw 'В Windows не установлен русский язык распознавания.'}
 $file=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($line)) ([Windows.Storage.StorageFile])
 $stream=Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
 try{
 $decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
 $bmp=Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
 try{$r=Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult]);$words=@();$row=0
 foreach($ocrLine in $r.Lines){
  foreach($word in $ocrLine.Words){$b=$word.BoundingRect;$words+=@{text=$word.Text;line=$row;x=$b.X;y=$b.Y;w=$b.Width;h=$b.Height}}
  $row++
 }
 $reply=@{text=(($r.Lines|ForEach-Object {$_.Text}) -join [Environment]::NewLine);words=$words;width=$bmp.PixelWidth;height=$bmp.PixelHeight}}finally{$bmp.Dispose()}
 }finally{$stream.Dispose()}
 }catch{$reply=@{error=$_.Exception.Message}}
 [Console]::WriteLine(($reply|ConvertTo-Json -Depth 6 -Compress))
}
