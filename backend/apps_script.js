/**
 * EliseAI Lead Intelligence — Google Apps Script
 *
 * Setup:
 *   1. Open your Google Sheet → Extensions → Apps Script
 *   2. Paste this entire file, replacing the default Code.gs content
 *   3. Set BACKEND_URL below to your Flask server (ngrok URL for local dev)
 *   4. Run installTrigger() once manually to register the onEdit trigger
 *   5. Grant the permissions it asks for
 *
 * How it works:
 *   - installTrigger() registers an onChange trigger on the spreadsheet
 *   - When a new row is inserted or an existing row is edited in columns A–G,
 *     processNewRow() fires and POSTs the lead data to your Flask /api/webhook
 *   - Flask enriches, scores, and writes results back to columns H–T
 */

var BACKEND_URL = "https://YOUR_NGROK_OR_PROD_URL/api/webhook";

// Column positions (1-indexed) — must match your sheet layout
var COL = {
  NAME:             1,
  EMAIL:            2,
  COMPANY:          3,
  PROPERTY_ADDRESS: 4,
  CITY:             5,
  STATE:            6,
  COUNTRY:          7,
  SCORE:            8,   // first output column — used to check if already processed
};


/**
 * Run this function ONCE manually (Run → Run function → installTrigger)
 * to register the spreadsheet onChange trigger.
 */
function installTrigger() {
  // Remove any existing triggers to avoid duplicates
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });

  ScriptApp.newTrigger("processNewRow")
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onChange()
    .create();

  SpreadsheetApp.getUi().alert("Trigger installed. New rows will be auto-processed.");
}


/**
 * Fired automatically by the onChange trigger.
 * Scans all rows for any that have input data but no score yet,
 * then sends each one to the backend.
 */
function processNewRow(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var lastRow = sheet.getLastRow();

  // Skip if only the header row exists
  if (lastRow < 2) return;

  // Check every data row — safe for concurrent edits / pasted batches
  for (var row = 2; row <= lastRow; row++) {
    var name  = sheet.getRange(row, COL.NAME).getValue();
    var city  = sheet.getRange(row, COL.CITY).getValue();
    var state = sheet.getRange(row, COL.STATE).getValue();
    var score = sheet.getRange(row, COL.SCORE).getValue();

    // Only process rows with the minimum required input and no existing score
    if (name && city && state && !score) {
      sendToBackend(sheet, row);
    }
  }
}


/**
 * POST a single row's lead data to the Flask webhook endpoint.
 */
function sendToBackend(sheet, row) {
  var payload = {
    row:              row,
    name:             sheet.getRange(row, COL.NAME).getValue(),
    email:            sheet.getRange(row, COL.EMAIL).getValue(),
    company:          sheet.getRange(row, COL.COMPANY).getValue(),
    property_address: sheet.getRange(row, COL.PROPERTY_ADDRESS).getValue(),
    city:             sheet.getRange(row, COL.CITY).getValue(),
    state:            sheet.getRange(row, COL.STATE).getValue(),
    country:          sheet.getRange(row, COL.COUNTRY).getValue() || "US",
  };

  var options = {
    method:      "post",
    contentType: "application/json",
    payload:     JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  try {
    var response = UrlFetchApp.fetch(BACKEND_URL, options);
    var code = response.getResponseCode();
    if (code !== 200) {
      Logger.log("Backend error for row " + row + ": HTTP " + code + " — " + response.getContentText());
    } else {
      Logger.log("Row " + row + " processed: " + response.getContentText());
    }
  } catch (err) {
    Logger.log("Failed to reach backend for row " + row + ": " + err.message);
  }
}


/**
 * Optional: add a custom menu to the sheet so reps can manually trigger
 * processing without opening the script editor.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("EliseAI")
    .addItem("Process Unscored Leads", "processAllUnscored")
    .addToUi();
}

function processAllUnscored() {
  processNewRow(null);
  SpreadsheetApp.getUi().alert("Done! Check the Score column for results.");
}
