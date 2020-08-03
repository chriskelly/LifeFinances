function New_Credit_Week() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Credit");
  Week_Row=sheet.createTextFinder("Week").findNext().getRow()+1
  Logger.log(Week_Row);
  sheet.insertRowBefore(Week_Row);
  var sourceRange = sheet.getRange("A"+(Week_Row+1)+":A"+(Week_Row+2));
  var destination = sheet.getRange("A"+(Week_Row)+":A"+(Week_Row+2));
  sourceRange.autoFill(destination, SpreadsheetApp.AutoFillSeries.DEFAULT_SERIES);
};
