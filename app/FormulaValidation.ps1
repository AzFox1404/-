function GetFormulaErrors($book){
 $errors=@()
 foreach($ws in $book.Worksheets){foreach($kind in @(-4123,2)){
  try{$bad=$ws.UsedRange.SpecialCells($kind,16);if($bad){$errors+=([string]$ws.Name+'!'+[string]$bad.Address(0,0))}}catch{}
 }}
 return $errors
}
