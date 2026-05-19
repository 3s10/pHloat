/**
 * pHloat Google Sheets Integration
 * Google Apps Script for receiving pH data and matching with Tilt readings
 * 
 * Setup Instructions:
 * 1. Create a new Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Replace Code.gs with this script
 * 4. Deploy as Web App (Execute as: Me, Who has access: Anyone)
 * 5. Copy the deployment URL and paste into pHloat Relay configuration
 * 
 * Sheet Structure:
 * - Each sensor gets its own sheet
 * - Columns: Timestamp, pH, Temperature, Specific Gravity (from Tilt), Color (from Tilt)
 */

// Configuration
const TIME_MATCH_WINDOW = 60; // seconds - match pH readings within ±60 seconds of Tilt reading

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    Logger.log('Received data: ' + JSON.stringify(data));
    
    const deviceName = data.device;
    const pH = parseFloat(data.pH);
    const temperature = parseFloat(data.temperature);
    const timestamp = new Date(data.timestamp);
    const readingNumber = parseInt(data.readingNumber);
    
    // Get or create sheet for this device
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(deviceName);
    
    if (!sheet) {
      sheet = ss.insertSheet(deviceName);
      // Add headers
      sheet.getRange(1, 1, 1, 6).setValues([[
        'Timestamp', 
        'pH', 
        'Temperature (°C)', 
        'Specific Gravity',
        'Tilt Color',
        'Reading #'
      ]]);
      sheet.getRange(1, 1, 1, 6).setFontWeight('bold');
      sheet.setFrozenRows(1);
    }
    
    // Find matching Tilt reading
    const tiltData = findMatchingTiltReading(timestamp, deviceName);
    
    // Append new row
    const newRow = [
      timestamp,
      pH,
      temperature,
      tiltData ? tiltData.gravity : '',
      tiltData ? tiltData.color : '',
      readingNumber
    ];
    
    sheet.appendRow(newRow);
    
    // Format the new row
    const lastRow = sheet.getLastRow();
    sheet.getRange(lastRow, 1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
    sheet.getRange(lastRow, 2).setNumberFormat('0.00');
    sheet.getRange(lastRow, 3).setNumberFormat('0.0');
    if (tiltData) {
      sheet.getRange(lastRow, 4).setNumberFormat('0.0000');
    }
    
    // Auto-resize columns
    sheet.autoResizeColumns(1, 6);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: 'success',
      message: 'Data logged successfully',
      tiltMatched: tiltData !== null
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    Logger.log('Error: ' + error.toString());
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function findMatchingTiltReading(targetTime, deviceName) {
  /**
   * Search for Tilt readings within TIME_MATCH_WINDOW seconds of the pH reading
   * This assumes you have a sheet with Tilt data
   * 
   * Expected Tilt sheet structure:
   * - Sheet name contains "Tilt" or matches a specific pattern
   * - Columns: Timestamp, Color, Temp, Gravity, etc.
   */
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  
  // Look for Tilt data sheet
  // This could be "Tilt Red", "Tilt Orange", etc., or a combined "Tilt Data" sheet
  for (let sheet of sheets) {
    const sheetName = sheet.getName();
    
    // Skip the pH sensor sheets
    if (sheetName === deviceName) continue;
    
    // Look for sheets that contain "Tilt" in the name
    if (sheetName.toLowerCase().includes('tilt')) {
      const tiltMatch = searchTiltSheet(sheet, targetTime);
      if (tiltMatch) {
        return tiltMatch;
      }
    }
  }
  
  return null;
}

function searchTiltSheet(sheet, targetTime) {
  const data = sheet.getDataRange().getValues();
  
  // Find column indices (assuming headers in row 1)
  const headers = data[0];
  let timestampCol = -1;
  let gravityCol = -1;
  let colorCol = -1;
  
  for (let i = 0; i < headers.length; i++) {
    const header = headers[i].toString().toLowerCase();
    if (header.includes('time') || header.includes('date')) {
      timestampCol = i;
    }
    if (header.includes('gravity') || header.includes('sg')) {
      gravityCol = i;
    }
    if (header.includes('color') || header.includes('name')) {
      colorCol = i;
    }
  }
  
  if (timestampCol === -1 || gravityCol === -1) {
    return null; // Can't find required columns
  }
  
  const targetTimeMs = targetTime.getTime();
  const windowMs = TIME_MATCH_WINDOW * 1000;
  
  // Search for closest match within time window
  let closestMatch = null;
  let closestDiff = Infinity;
  
  for (let i = 1; i < data.length; i++) { // Start at 1 to skip headers
    const row = data[i];
    const rowTime = new Date(row[timestampCol]);
    const rowTimeMs = rowTime.getTime();
    
    const diff = Math.abs(targetTimeMs - rowTimeMs);
    
    if (diff <= windowMs && diff < closestDiff) {
      closestDiff = diff;
      closestMatch = {
        gravity: row[gravityCol],
        color: colorCol >= 0 ? row[colorCol] : '',
        timestamp: rowTime,
        timeDiff: diff / 1000 // in seconds
      };
    }
  }
  
  return closestMatch;
}

/**
 * Test function - run this to verify the script works
 */
function testDoPost() {
  const testData = {
    postData: {
      contents: JSON.stringify({
        device: 'Test-Fermenter',
        pH: 4.52,
        temperature: 18.5,
        timestamp: new Date().toISOString(),
        readingNumber: 1
      })
    }
  };
  
  const result = doPost(testData);
  Logger.log(result.getContent());
}

/**
 * Alternative: If you want to manually add Tilt data to this same sheet
 * You can use this function with the Tilt Google Sheets logging
 */
function doGet(e) {
  // This allows you to log Tilt data to the same spreadsheet
  // URL format: ?color=Red&gravity=1.050&temp=68&timestamp=...
  
  try {
    const color = e.parameter.color;
    const gravity = parseFloat(e.parameter.gravity);
    const temp = parseFloat(e.parameter.temp);
    const timestamp = new Date(e.parameter.timestamp || new Date());
    
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName('Tilt ' + color);
    
    if (!sheet) {
      sheet = ss.insertSheet('Tilt ' + color);
      sheet.getRange(1, 1, 1, 4).setValues([[
        'Timestamp', 'Color', 'Temperature (°F)', 'Specific Gravity'
      ]]);
      sheet.getRange(1, 1, 1, 4).setFontWeight('bold');
    }
    
    sheet.appendRow([timestamp, color, temp, gravity]);
    
    return ContentService.createTextOutput('OK');
    
  } catch (error) {
    return ContentService.createTextOutput('Error: ' + error.toString());
  }
}
