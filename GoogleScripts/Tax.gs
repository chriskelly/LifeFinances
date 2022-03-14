function calcSS() {
  var Tax_sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Tax")
  //find Indexed Earnings range
  var his_cell=Tax_sheet.createTextFinder("Indexed Earnings (His)").findNext();
  var her_cell=Tax_sheet.createTextFinder("Indexed Earnings (Hers)").findNext();
  //make array of all incomes sorted from largest to smallest
  var his_incomes = Tax_sheet.getRange(his_cell.getRow()+1, his_cell.getColumn(), 100, 1).getValues().sort().reverse(); 
  var her_incomes = Tax_sheet.getRange(her_cell.getRow()+1, her_cell.getColumn(), 9, 1).getValues().sort().reverse(); //only 9 years of not working for de anza
  var first_bracket= Get_Parameter("First Bracket")
  var second_bracket= Get_Parameter("Second Bracket")

  His_Max_Benefit=Monthly_Benefit_Calc(his_incomes);
  His_Min_Benefit=His_Max_Benefit*.725;
  Her_Max_Benefit=Monthly_Benefit_Calc(her_incomes);
  Her_Min_Benefit=Her_Max_Benefit*.725;
  
  Tax_sheet.createTextFinder("His Max SS").findNext().offset(0,1).setValue(His_Max_Benefit);
  Tax_sheet.createTextFinder("His Min SS").findNext().offset(0,1).setValue(His_Min_Benefit);
  Tax_sheet.createTextFinder("Her Max SS").findNext().offset(0,1).setValue(Her_Max_Benefit);
  Tax_sheet.createTextFinder("Her Min SS").findNext().offset(0,1).setValue(Her_Min_Benefit);

//Calculates max monthly benefit  given full log of sorted earnings years
function Monthly_Benefit_Calc(earnings){ 
  var sum = 0
  for (var i=0;i<Math.min(34,earnings.length);i++){ //only top 35 years count
    sum+=earnings[i][0]
  }
  var Avg_monthly_earnings = sum/420 // 35 years * 12 months/year
  var Monthly_Benefit
  //brackets are meant to limit how much higher incomes can lead to higher benefits
  if(Avg_monthly_earnings>second_bracket){
    Monthly_Benefit = first_bracket*0.9+second_bracket*0.32+(Avg_monthly_earnings-second_bracket)*0.15
  }else if(Avg_monthly_earnings>first_bracket){
    Monthly_Benefit = first_bracket*0.9+(Avg_monthly_earnings-first_bracket)*0.32
  }else{
    Monthly_Benefit = Avg_monthly_earnings*0.9
  }
  return Monthly_Benefit
}
  function Get_Parameter(s){
    return Tax_sheet.createTextFinder(s).findNext().offset(0,1).getValue()
  }
}
