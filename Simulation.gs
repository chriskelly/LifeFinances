function Main(){  
  //Troubleshooting
  //Did you rename parameters?
  //Did you move columns/rows? including the tax sheet?
  //if you're adding a column, you'll need to bump all the column numeric references up to compensate
  
  //Set sheets
  var Sim_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Simulation")
  var Param_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Parameters")
  var stockReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("StockReturns")
  var bondReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("BondReturns")
  var REReturns_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("REReturns")
  var Tax_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Tax")
  var Dashboard_Sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Dashboard")
  
  //Get all parameters from Parameter and Tax (SS/Pension) page
  var AllParams = Param_Sheet.getRange(2,1,100,2).getValues().concat(Param_Sheet.getRange(2,4,100,2).getValues()).concat(Param_Sheet.getRange(2,7,100,2).getValues()).concat(Param_Sheet.getRange(2,10,100,2).getValues()).concat(Tax_Sheet.getRange(19,10,14,2).getValues())
  AllParams = filterSpaces(AllParams)
  //Get trial parameters
  var TrialParamsList = Param_Sheet.getRange(3,21,100,1).getValues()
  TrialParamsList = filterSpaces(TrialParamsList)
  updateProgress(0)
  
  //Pull in generated random returns
  var trials = Get_Param("Monte Carlo Trials") //max 5000
  var stockReturns = stockReturns_Sheet.getSheetValues(1, 1, 71, trials)
  var bondReturns = bondReturns_Sheet.getSheetValues(1, 1, 71, trials)
  var REReturns = REReturns_Sheet.getSheetValues(1, 1, 71, trials)
  updateProgress(1)
  
  //Run initial fill and simulate
  fillAllYearsArray(true)
  simulate(true)
  updateProgress(2)
  
  //------------------------------------------------------------------
  //Create trial array from parameter sheet trials: [Trial_1[Param_1[key,value]]]
  var TrialArr = []
  for(a=0;a<TrialParamsList.length;a++){
    var TrialParamsStr = TrialParamsList[a][0]
    var TrialParams = TrialParamsStr.split(",")
    var ParamArr = []
    for(b=0;b<TrialParams.length;b++){
      var ParamStr = TrialParams[b]
      var Param = ParamStr.split("|")
      ParamArr.push(Param)
      }
    TrialArr.push(ParamArr)
  }
  //Create custom TrialArr. Current design is trying out different Allocation combos. Try to limit to 100 total iter (~set#^options)
//  var CustomTrialArr = []
//  var ParamSet1 = ["Equity FI Proportion",0,.2,.4,.6,.8,1];
//  var ParamSet2 = ["Bond FI Proportion",0,.2,.4,.6,.8,1];
//  var ParamSet3 = ["RE FI Proportion",0,.2,.4,.6,.8,1];
//  var CustomTrialName =[]
//  for(var a =1; a<ParamSet1.length; a++){
//    for(var b =1; b<ParamSet2.length; b++){
//      for(var c =1; c<ParamSet3.length; c++){
//        if(ParamSet1[a]+ParamSet2[b]+ParamSet3[c]==1){ //confirm it's a valid combination
//          var tempTrial = [[ParamSet1[0],ParamSet1[a]],[ParamSet2[0],ParamSet2[b]],[ParamSet3[0],ParamSet3[c]]]
//          CustomTrialArr.push(tempTrial);
//          CustomTrialName.push([[tempTrial[0].join("-"),tempTrial[1].join("-"),tempTrial[2].join("-")].join(", ")])
//        }
//      }
//    }
//  }
//  Logger.log(CustomTrialArr.length); //do this sanity check first before trying to setValues
//  TrialArr=CustomTrialArr;
//  Param_Sheet.getRange(3,21,CustomTrialName.length).setValues(CustomTrialName);
  
  
  //Replace AllParams parameters with Trial parameters
  var multiResults =[] //intialize outside of function to prevent reset during loop
  for(var e=0; e<TrialArr.length; e++){
    AllParams = Param_Sheet.getRange(2,1,100,2).getValues().concat(Param_Sheet.getRange(2,4,100,2).getValues()).concat(Param_Sheet.getRange(2,7,100,2).getValues()).concat(Param_Sheet.getRange(2,10,100,2).getValues()).concat(Tax_Sheet.getRange(19,10,14,2).getValues())
    AllParams = filterSpaces(AllParams) //reset AllParams. Could not figure out a more effiecient way. Tried to record initial params, but kept getting linked to AllParams
    for(var d=0; d<TrialArr[e].length;d++){
      for(var c=0; c<AllParams.length; c++) {
        if(AllParams[c][0] == TrialArr[e][d][0]) { //find all the parameters in the trial list and insert them into the AllParams list
          AllParams[c][1]=TrialArr[e][d][1];
        }
      }
    }
    fillAllYearsArray(false)
    simulate(false)
    updateProgress(3+e)
  }
  if(multiResults.length>0){Param_Sheet.getRange(3,19,multiResults.length,2).setValues(multiResults);}// W/o if() statement, kept throwing errors if there were no trial parameters
  
  //------------------------------------------------------------------------------------------------------------------------------------------------
  function fillAllYearsArray(fill){ //giant array creation that will fill the Simulate sheet
      
  //Set variables needed multiple times
  //Even if Col # changed here, order to array push needs to also be changed!
  AllYears = []
  CurrentYear = Get_Param("His Age")+1993
  FIYear = Get_Param("FI Year")
  InflatEst = 1+Get_Param("Inflation (%)")
  YearCol = 0
  YearsTillCol = 1
  TimeCol =2
  FICol = 3
  SavingsCol = 4
  CPICol = 5
  InflationCol = 6
  HisIncomeCol = 7
  HerIncomeCol = 8
  TaxDeferedCol = 9
  PensionCol = 10
  HisSSCol = 11
  HerSSCol = 12
  TotalIncomeCol = 13
  TaxCol = 14
  SpendingCol = 15
  KidsCol = 16
  TotalCostsCol =17
  SaveRateCol = 18
  ContributeCol = 19
  StockAlcCol = 20
  REAlcCol = 21
  BondAlcCol = 22
  MarginCol = 23
  StockReturnPctCol = 24
  REReturnPctCol = 25	
  BondReturnPctCol = 26
  ReturnPctCol = 27
  ReturnAmtCol = 28
    
  //Loops through individual years, adding every column, then creating multi-dimensional array with every year
  for(var x=CurrentYear;x<=2090;x++){ 
    var SingleYear =[]
    SingleYear.push(Get_Year(x-CurrentYear));
    SingleYear.push(Get_YearsTill(SingleYear[YearCol]));//pass through Year
    SingleYear.push(Get_Time(SingleYear[YearCol]));
    SingleYear.push(Get_FI(SingleYear[YearCol]));
    SingleYear.push(Get_Savings(SingleYear[TimeCol]));
    SingleYear.push(Get_CPI(SingleYear[YearsTillCol]));//pass through years till
    SingleYear.push(InflatEst);
    SingleYear.push(Get_Income(SingleYear[YearsTillCol],SingleYear[FICol],Get_Param("His Total Income")));//pass through years till and FI State
    SingleYear.push(Get_Income(SingleYear[YearsTillCol],SingleYear[FICol],Get_Param("Her Total Income")));
    SingleYear.push(Get_TaxDefered(SingleYear[YearsTillCol],SingleYear[FICol]));
    SingleYear.push(Get_Pension(SingleYear[YearCol],SingleYear[YearsTillCol],Get_Param("Early Pension")));//pass through Year and Years till
    SingleYear.push(Get_HisSS(SingleYear[YearCol],SingleYear[YearsTillCol],Get_Param("Early SS")));
    SingleYear.push(Get_HerSS(SingleYear[YearCol],SingleYear[YearsTillCol],Get_Param("Early SS")));
    SingleYear.push(SingleYear[HisIncomeCol]+SingleYear[HerIncomeCol]+SingleYear[PensionCol]+SingleYear[HisSSCol]+SingleYear[HerSSCol]);//Total Income = add Incomes to Pension and SSs
    SingleYear.push((SingleYear[HisIncomeCol]+SingleYear[HerIncomeCol]-SingleYear[TaxDeferedCol]+0.8*(SingleYear[PensionCol]+SingleYear[HisSSCol]+SingleYear[HerSSCol]))*Get_Param("Tax (%)"));//Tax = tax on all income minus tax deductable and 80% of pension/SSs
    SingleYear.push(Get_Spending(SingleYear[YearsTillCol],SingleYear[FICol],SingleYear[YearCol]));
    SingleYear.push(Get_Kids(SingleYear[YearCol],SingleYear[SpendingCol]));
    SingleYear.push(SingleYear[TaxCol]+SingleYear[SpendingCol]+SingleYear[KidsCol]);//Total Costs = add Spending+Tax+Kids
    SingleYear.push(Get_SR(SingleYear[TotalIncomeCol],SingleYear[TaxCol],SingleYear[SpendingCol],SingleYear[TotalCostsCol]));
    SingleYear.push(SingleYear[TotalIncomeCol]-SingleYear[TotalCostsCol]); //Contribution = Income-costs
    var Allocation = Get_Allocation(SingleYear[YearCol]) //pass through FI State
    SingleYear.push(Allocation[0]); //equity allocation
    SingleYear.push(Allocation[2]); //RE allocation
    SingleYear.push(Allocation[1]); //bond allocation
    SingleYear.push(Get_Margin(SingleYear[YearsTillCol],SingleYear[SavingsCol]));
    SingleYear.push(Get_StockReturn());
    SingleYear.push(Get_REReturn());
    SingleYear.push(Get_BondReturn());
    SingleYear.push(SingleYear[StockAlcCol]*SingleYear[StockReturnPctCol]+SingleYear[BondAlcCol]*SingleYear[BondReturnPctCol]+SingleYear[REAlcCol]*SingleYear[REReturnPctCol]); //Return Rate = allocations x performances
    SingleYear.push(SingleYear[ReturnPctCol]*(SingleYear[SavingsCol]+SingleYear[MarginCol]+0.5*SingleYear[ContributeCol])-SingleYear[MarginCol]*Get_Param("Interest Rate")); //Return($) = returnRate*(Savings+Margin+.5*Contributions)-Margin cost
    AllYears.push(SingleYear)
  }
    if(fill){Sim_Sheet.getRange(2,1,AllYears.length,AllYears[0].length).setValues(AllYears);}
  }
  
  //------------------------------------------------------------------------------------------------------------------------------------------------
  function simulate(frontPage){
  //cycle through columns of random returns for a monte carlo simulation
  //To save time, only doing calculations on columns that are affected by the return rate
  //in each loop, start with initial Savings (net worth), bring in next return rates, calculate new return (need contribution amount), calculate next savings
  var success = 0;
  var worst = 0;
  var best = 0
  var Savings = Get_Param("Current Net Worth ($)")
  var EndResults =[]
  var lowMargin = 0
  var oldSuccess = 0
  var newSuccess = 0
  //loop through each row of generated returns, then each column for an additional trial
  //everything "old" is just a test to see if you would have been better off not using margin. Safe to remove
  for(var col=0;col<trials;col++){
    var tempSavings = Savings
    var oldSavings = Savings
    var tempMargin = Savings*Get_Param("Margin")
    for(var row=0;row<70;row++){
      var stockRate=stockReturns[row][col]
      var bondRate=bondReturns[row][col]
      var RERate=REReturns[row][col]
      var ReturnRate = stockRate*AllYears[row][StockAlcCol]+bondRate*AllYears[row][BondAlcCol]+RERate*AllYears[row][REAlcCol];
      //var Return = ReturnRate*(tempSavings+0.5*AllYears[row][ContributeCol]+tempMargin)-tempMargin*(Get_Param("Interest Rate"))
      var Return = TEST3_Get_Return(row,stockRate,bondRate,tempSavings,ContributeCol,RERate);
      var oldReturn = ReturnRate*(oldSavings+0.5*AllYears[row][ContributeCol])
      tempSavings = tempSavings + Return+AllYears[row][ContributeCol];
      oldSavings = oldSavings + oldReturn+AllYears[row][ContributeCol];
      tempMargin = Math.max(tempMargin,tempSavings*Get_Param("Margin"));
    }
    EndResults.push(tempSavings)
    if(tempSavings>0){success=success+1}
    if(tempSavings>0 && oldSavings<0){newSuccess=newSuccess+1}
    if(tempSavings<0 && oldSavings>0){oldSuccess=oldSuccess+1}
    if(tempSavings>best){best=tempSavings}
    if(tempSavings<worst){worst=tempSavings}
  }
  //Logger.log(newSuccess)
  //Logger.log(oldSuccess)
  var Results = []
  var successRate = [success/trials]
  Results.push(successRate)
  Results.push([worst])
  Results.push([best])
  Results.push([standardDeviation(EndResults)])
  if(frontPage){Dashboard_Sheet.getRange(16,3,4).setValues(Results);}//write first set of results to Dashboard, any other results are from trials and are sent to Parameter page in the multiResults array
    else{multiResults.push([Results[0],Results[3]]);}
  }

  //---------------------------------------------------------------------------------------------------------------------------------------------------------
  //All columnn functions
  function Get_Year(delta){
    return CurrentYear+delta;
  }
 function Get_YearsTill(Year){
    var ActualYear = Utilities.formatDate(new Date(), "GMT+1", "yyyy")
    return Year-ActualYear;
  } 
  function Get_Time(Year){
    if (Year>CurrentYear) {return "Future"} 
    else if (Year=CurrentYear) {return "Present"} 
    else {return "Past"}
  }
  function Get_FI(Year){
    if (Year<FIYear) {return false} 
    else {return true}
  } 
  function Get_Savings(Time){
    if (Time=="Present") {return Get_Param("Current Net Worth ($)")} 
    else {
      var PrevSav = AllYears[AllYears.length-1][SavingsCol];
      var PrevContribution = AllYears[AllYears.length-1][ContributeCol]
      var PrevReturn = AllYears[AllYears.length-1][ReturnAmtCol]
      return PrevSav+PrevContribution+PrevReturn
    }
  }
  function Get_Margin(YearsTill,Savings){
    var RERatio = Get_Param("RE Ratio")
    var EquityTarget = Get_Param("Equity Target") 
    var rate = Get_Param("Inflation (%)")
    var MaxRiskFactor = Get_Param("Max Risk Factor")
    
    var nper = FIYear-CurrentYear-YearsTill 
    var EquityTargetPV = EquityTarget / Math.pow(1 + rate, nper); 
    var RiskFactor = Math.min(Math.max(EquityTargetPV/Savings,0),MaxRiskFactor)
    var REAlloc = (RiskFactor*RERatio)/((1-RERatio)*(1+RiskFactor*RERatio/(1-RERatio))) //derived with fun algebra! ReAlloc = RERatio*(ReAlloc+EquityTotal); EquityTotal = RiskFactor*OriginalEquity; ReAlloc+OriginalEquity=100%
    var EquityAlloc = (1-REAlloc)*RiskFactor
    return Math.max(0,(REAlloc+EquityAlloc-1)*Savings)
  }
  function Get_CPI(YearsTill){
    var Current = Get_Param("Current CPI")
    return Current*Math.pow(InflatEst,YearsTill);
  } 
  function Get_Income(YearsTill,FIState,Income){
    if (FIState==true) {return 0} 
    else {return Income*Math.pow(InflatEst+Get_Param("Raise (%)"),YearsTill)}
  }
  function Get_TaxDefered(YearsTill,FIState){
    var His = Get_Param("His Tax Deferrable")
    var Hers = Get_Param("Her Tax Deferrable")   
    if (FIState==true) {return 0} 
    else {return (His+Hers)*Math.pow(InflatEst,YearsTill)}
  }
  function Get_Pension(Year,YearsTill,EarlyPension){
    PensionYears = Param_Sheet.getRange(3,13,13).getValues();
    EarlyPensionYear = PensionYears[0];
    LatePensionYear = PensionYears[12];
    if (EarlyPension) {
      var PensionYear=EarlyPensionYear;
      var PensionAmount=Get_Param("Her Min Pension (Yearly)");
    } 
    else {
      var PensionYear=LatePensionYear;
      var PensionAmount=Get_Param("Her Max Pension (Yearly)");
    }
    if (Year<PensionYear) {return 0} 
    else {return PensionAmount/1000*Math.pow(InflatEst,YearsTill)}
  }
  function Get_HisSS(Year,YearsTill,EarlySS){
    if (EarlySS) {
      var SSYear=Get_Param("Early SS Age")+1992;
      var SSAmount=Get_Param("His Min SS");
    } 
    else {
      var SSYear=Get_Param("Late SS Age")+1992;
      var SSAmount=Get_Param("His Max SS");
    }
    if (Year<SSYear) {return 0} 
    else {return SSAmount/1000*12*Math.pow(InflatEst,YearsTill)}
  }
  function Get_HerSS(Year,YearsTill,EarlySS){
    if (EarlySS) {
      var SSYear=Get_Param("Early SS Age")+1987;
      var SSAmount=Get_Param("Her Min SS");
    } 
    else {
      var SSYear=Get_Param("Late SS Age")+1987;
      var SSAmount=Get_Param("Her Max SS");
    }
    if (Year<SSYear) {return 0} 
    else {return SSAmount/1000*12*Math.pow(InflatEst,YearsTill)}
  }
  function Get_Spending(YearsTill,FIState,Year){
    var multiplier =1
    var NomadYears = Get_Param("Nomad Years")
    if (FIState==true) {multiplier = 1+Get_Param("Retirement Change (%)")} 
    if (FIState==true && Year-FIYear<NomadYears){multiplier = 0.54} //at the time of creation, 0.54*73.8 = $40k/year
    return multiplier*Get_Param("Total Spending (Yearly)")*Math.pow(InflatEst,YearsTill)
  }
  function Get_Kids(Year,Spending){
    var KidYears =[Get_Param("Year @ Kid #1"),Get_Param("Year @ Kid #2"),Get_Param("Year @ Kid #3")]
    var CurrentKids = 0;
    for(var i=0;i<KidYears.length;i++){
      if(Year>=KidYears[i]&&Year-22<KidYears[i]){CurrentKids = CurrentKids+1}
    }
    return CurrentKids*Spending*Get_Param("Cost of Kid (% Spending)")
  }
  function Get_SR(TotalIncome,Tax,Spending,TotalCosts){
    if (TotalIncome<Spending) {return 0} 
    else {return 1-(TotalCosts-Tax)/(TotalIncome-Tax)}
  }
  function Get_Allocation(Year){
    var Allocation=[];
    if(Year>=FIYear+Get_Param("Years postFI Alc Switch")){
      Allocation[0] = Get_Param("Equity FI Proportion")
      Allocation[1] = Get_Param("Bond FI Proportion")
      Allocation[2] = Get_Param("RE FI Proportion")
    }
    else{
      Allocation[0] = Get_Param("Equity Proportion")
      Allocation[1] = Get_Param("Bond Proportion")
      Allocation[2] = Get_Param("RE Proportion")
    }
    return Allocation
  }
  function Get_StockReturn(){return Get_Param("Equity Return (%)")}
  
  function Get_BondReturn(){return Get_Param("Bond Return (%)")}
  
  function Get_REReturn(){return Get_Param("RE Return (%)")}
  
  //-------------------------------------------------------------------------------------------------------------------------------------------------
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
      if(pair[0]==s){
        if(pair[1]=="false"){return false;}
        else if(pair[1]=="true"){return true;}
        else if(Number(pair[1])!=Number(pair[1])){return pair[1];}
        else{return Number(pair[1]);}
        
      }
    }    
   }
  
  function standardDeviation(values){
    var avg = average(values);
    Logger.log(avg)
    var squareDiffs = values.map(function(value){
      var diff = value - avg;
      var sqrDiff = diff * diff;
      return sqrDiff;
    });
    var avgSquareDiff = average(squareDiffs);
    var stdDev = Math.sqrt(avgSquareDiff);
    return stdDev;
  }

  function average(data){
    var sum = data.reduce(function(sum, value){
      return sum + value;
    }, 0);
    var avg = sum / data.length;
    return avg;
  }
  
  //Assumes fixed positioning for Progress marks. First when finished importing in returns, second after initial simulation, then one after each trial.
  function updateProgress(station){
    var dashesNeeded = 27; //based on total number of dashes that can fit inside Dashboard cell
    var numTrials = TrialParamsList.length
    var dashesEachSegment = Math.round(dashesNeeded/(numTrials+2))
    var dashes = ""
    for (var d=0;d<dashesEachSegment;d++){ 
        dashes = dashes.concat("|") //builds up dash segment
    }
    var Progress = ""
    for (var s=0;s<station;s++){
        Progress = Progress.concat(dashes) //how many dash segments should there be now
    }
    Dashboard_Sheet.getRange(15,3).setValue(Progress)
    SpreadsheetApp.flush(); //forces refresh so you can see bar
  }


    //-----------------TESTS-----------------//

  function TEST_Get_Return(row,stockRate,bondRate,tempSavings,ContributeCol,RERate){
    var LifecycleTarget = Get_Param("Lifecycle Target") 
    var EquityTarget = Get_Param("Equity Target") 
    var rate = Get_Param("Inflation (%)")
    
    //var SavingsTarget = AllYears[FIYear-CurrentYear][SavingsCol] 
    var nper = FIYear-CurrentYear-row 
    //var SavingsTargetPV = SavingsTarget / Math.pow(1 + rate, nper); 
    //var EquityTarget = SavingsTargetPV*LifecycleTarget 
    var EquityTargetPV = EquityTarget / Math.pow(1 + rate, nper); 
    //var EquityAlloc = Math.max(LifecycleTarget,Math.min(EquityTargetPV/tempSavings,2)) //original interpretation of Lifecycle investing, but provides significantly worse results
    var EquityAlloc = Math.min(Math.max(EquityTargetPV/tempSavings,0),2)
    var BondAlloc = Math.max(1-EquityAlloc,0) 
    var ReturnRate = stockRate*EquityAlloc+bondRate*BondAlloc 
    
    //if(row==0){Logger.log(EquityTarget)}
    //if(EquityAlloc<2){Logger.log(row+", "+stockRate+", "+EquityAlloc+", "+tempSavings)}
    //Logger.log(row+", "+EquityAlloc+", "+tempSavings)
  
    return ReturnRate*(tempSavings+0.5*AllYears[row][ContributeCol])-tempSavings*Math.max(EquityAlloc-1,0)*(Get_Param("Interest Rate")) 
  }
  
  function TEST2_Get_Return(row,stockRate,bondRate,tempSavings,ContributeCol,RERate){
    var StartEquity = Get_Param("Start Equity")
    var WorkEndEquity = Get_Param("Work End Equity")
    var RetireStartEquity = Get_Param("Retire Start Equity")
    var EndEquity = Get_Param("End Equity")
    
    var TimeBeforeFI = FIYear-CurrentYear
    var TimeAfterFI = 70-TimeBeforeFI
    var YearsSinceFI = row-TimeBeforeFI
    
    if(YearsSinceFI<0){
      var YearsTilFI = -YearsSinceFI
      var EquityAlloc = (StartEquity-WorkEndEquity)/TimeBeforeFI*YearsTilFI+WorkEndEquity
    } else{
      var EquityAlloc = (EndEquity-RetireStartEquity)/TimeAfterFI*YearsSinceFI+RetireStartEquity
    }
    var BondAlloc = Math.max(1-EquityAlloc,0) 
    var ReturnRate = stockRate*EquityAlloc+bondRate*BondAlloc 
            
    return ReturnRate*(tempSavings+0.5*AllYears[row][ContributeCol])-tempSavings*Math.max(EquityAlloc-1,0)*(Get_Param("Interest Rate")) 
  }
  
  function TEST3_Get_Return(row,stockRate,bondRate,tempSavings,ContributeCol,RERate){
    var RERatio = Get_Param("RE Ratio")
    var EquityTarget = Get_Param("Equity Target") 
    var LifecycleTarget = Get_Param("Lifecycle Target") 
    var rate = Get_Param("Inflation (%)")
    var MaxRiskFactor = Get_Param("Max Risk Factor")
    
    var nper = FIYear-CurrentYear-row 
    var EquityTargetPV = EquityTarget / Math.pow(1 + rate, nper); 
    var RiskFactor = Math.min(Math.max(EquityTargetPV/tempSavings,0),MaxRiskFactor)
    var REAlloc = (RiskFactor*RERatio)/((1-RERatio)*(1+RiskFactor*RERatio/(1-RERatio))) //derived with fun algebra! ReAlloc = RERatio*(ReAlloc+EquityTotal); EquityTotal = RiskFactor*OriginalEquity; ReAlloc+OriginalEquity=100%
    var EquityAlloc = (1-REAlloc)*RiskFactor
    var BondAlloc = Math.max(1-REAlloc-EquityAlloc,0) 
    var ReturnRate = stockRate*EquityAlloc+bondRate*BondAlloc+RERate*REAlloc
    //if(row==0){Logger.log(EquityTarget)}
    //if(EquityAlloc<2){Logger.log(row+", "+stockRate+", "+EquityAlloc+", "+tempSavings)}
    //Logger.log(row+", "+REAlloc+", "+EquityAlloc+", "+BondAlloc+", "+tempSavings)
  
    return ReturnRate*(tempSavings+0.5*AllYears[row][ContributeCol])-tempSavings*Math.max(EquityAlloc-1,0)*(Get_Param("Interest Rate")) 
  }
}

  
//  How to do a time stamp
//  var first_d = new Date();
//  var fristTimeStamp = first_d.getTime();
//  var next_d = new Date();
//  var nextTimeStamp = next_d.getTime();
//  Logger.log(nextTimeStamp-fristTimeStamp)
