function RandomReturns() {
  var stockReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("StockReturns")
  var bondReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("BondReturns")
  var REReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("REReturns")
  var Param_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Parameters")
  
  //Get all parameters
  var AllParams = Param_Sheet.getRange(2,16,15,2).getValues()
  AllParams = filterSpaces(AllParams)
  
  //Set parameters from AllParams
  var WholeRange = "A1:GJH71" //5000 columns: GJH
  var EquityMean=Get_Param("Equity Mean");
  var EquityStDev=Get_Param("Equity Stdev");
  var EquityAnnHigh=Get_Param("Equity Annual High");
  var EquityAnnLow=Get_Param("Equity Annual Low");
  var BondMean=Get_Param("Bond Mean");
  var BondStDev=Get_Param("Bond Stdev");
  var BondAnnHigh=Get_Param("Bond Annual High");
  var BondAnnLow=Get_Param("Bond Annual Low");
  var REMean=Get_Param("RE Mean");
  var REStDev=Get_Param("RE Stdev");
  var REAnnHigh=Get_Param("RE Annual High");
  var REAnnLow=Get_Param("RE Annual Low");
  
  //CANNOT RUN FULL PROGRAM (EXCEEDS EXECUTION TIME). RUN ONE AT A TIME!
//  stockReturns_Sheet.clear()
//  Fill_Sheet(stockReturns_Sheet.getRange(WholeRange),EquityMean,EquityStDev,EquityAnnHigh,EquityAnnLow)
//  bondReturns_Sheet.clear()
//  Fill_Sheet(bondReturns_Sheet.getRange(WholeRange),BondMean,BondStDev,BondAnnHigh,BondAnnLow)
  REReturns_Sheet.clear()
  Fill_Sheet(REReturns_Sheet.getRange(WholeRange),REMean,REStDev,REAnnHigh,REAnnLow)
  
  function Fill_Sheet(range,mean,stdev,High,Low){
    var result = 0
    var annualized = 0;
    var iter = 0
    var MultiReturns=[];
    for (var x = 1; x <= range.getWidth(); x++) {
      annualized=0
      while(annualized<Low||annualized>High){ 
        var SingleReturns=[];
        var product =1;
        for (var y = 1; y <= range.getHeight(); y++){
          var yield = mean+(2*Math.random()-1)*stdev*2;
          SingleReturns.push(yield-1)
          product = product*yield;
        }
        annualized = Math.pow(product,1/range.getHeight());
        iter = iter+1;
      }
      MultiReturns.push(SingleReturns)
    }
    MultiReturns = transpose(MultiReturns);
    range.setValues(MultiReturns);
    Logger.log("Completed. Iterations: "+iter);
  }

  //Get rid of empty spaces in multi-dimensional array (can't use array.filter)
  function filterSpaces(array){
    var filtered = [];
    for(var i = 0; i < array.length; i++){
      var obj = array[i];
      if(obj[0]!=""){filtered.push(obj);}
    }    
    return filtered;
  }
  
  //Pull Parameters from AllParams list
  function Get_Param(s){
    for(var i = 0; i < AllParams.length; i++){
      var pair = AllParams[i];
      if(pair[0]==s){return pair[1];}
    }    
   }
  
  function transpose(a){
    return Object.keys(a[0]).map(function (c) { return a.map(function (r) { return r[c]; }); });
  }
}
