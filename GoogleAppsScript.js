/**
 * pHloat Google Sheets Integration
 *
 * Implements integration/upload_contract.json (v1).
 * Same JSON payload and X-pHloat-Token auth as Tilt Pi POST /api/ph.
 *
 * Setup:
 * 1. Create a Google Sheet
 * 2. Extensions > Apps Script — paste this file
 * 3. Project Settings > Script properties:
 *      PHLOAT_UPLOAD_SECRET = (same token as relay / Tilt Pi config)
 * 4. Deploy as Web App (Execute as: Me, Who has access: Anyone)
 * 5. Paste deployment URL into relay "Google Sheets URL"
 *
 * Auth: Apps Script web apps cannot read request headers, so the token is
 * carried in the request BODY (POST: {"token": "<secret>", ...}) or as a
 * query PARAMETER (GET: ?token=<secret>). The relay sends it in the body
 * automatically. (The Tilt Pi server, which can read headers, still uses the
 * X-pHloat-Token header.)
 */

const TIME_MATCH_WINDOW = 60; // seconds

function getUploadSecret_() {
  return PropertiesService.getScriptProperties().getProperty('PHLOAT_UPLOAD_SECRET') || '';
}

// Constant-time string comparison (avoids leaking the secret via timing).
function constantTimeEquals_(a, b) {
  a = String(a || '');
  b = String(b || '');
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

// Apps Script web apps do NOT expose request headers to doPost/doGet, so the
// token cannot be read from an X-pHloat-Token header. The caller passes the
// token taken from the request BODY (POST) or query PARAMETER (GET).
function verifyUploadToken_(supplied) {
  const expected = getUploadSecret_();
  if (!expected) {
    throw new Error('PHLOAT_UPLOAD_SECRET is not set in Script Properties');
  }
  if (!constantTimeEquals_(supplied, expected)) {
    throw new Error('Unauthorized');
  }
}

function sanitizeDeviceName_(name) {
  const cleaned = String(name || '').replace(/[^A-Za-z0-9_-]/g, '');
  return cleaned || 'Sensor';
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    verifyUploadToken_(data.token);   // token travels in the JSON body

    const deviceName = sanitizeDeviceName_(data.device);
    const pH = parseFloat(data.pH);
    const temperature = parseFloat(data.temperature);
    const timestamp = new Date(data.timestamp);
    const readingNumber = parseInt(data.readingNumber, 10);

    if (isNaN(pH) || pH < 0 || pH > 14) {
      throw new Error('Invalid pH value');
    }
    if (isNaN(timestamp.getTime())) {
      throw new Error('Invalid timestamp');
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(deviceName);

    if (!sheet) {
      sheet = ss.insertSheet(deviceName);
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

    const tiltData = findMatchingTiltReading_(timestamp, deviceName);

    sheet.appendRow([
      timestamp,
      pH,
      temperature,
      tiltData ? tiltData.gravity : '',
      tiltData ? tiltData.color : '',
      readingNumber
    ]);

    const lastRow = sheet.getLastRow();
    sheet.getRange(lastRow, 1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
    sheet.getRange(lastRow, 2).setNumberFormat('0.00');
    sheet.getRange(lastRow, 3).setNumberFormat('0.0');
    if (tiltData) {
      sheet.getRange(lastRow, 4).setNumberFormat('0.0000');
    }
    sheet.autoResizeColumns(1, 6);

    return ContentService.createTextOutput(JSON.stringify({
      status: 'success',
      message: 'Data logged successfully',
      tiltMatched: tiltData !== null
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    Logger.log('Error: ' + error.toString());
    const status = error.message === 'Unauthorized' ? 401 : 500;
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function findMatchingTiltReading_(targetTime, deviceName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  let bestMatch = null;
  let bestDiff = Infinity;

  for (const sheet of sheets) {
    const sheetName = sheet.getName();
    if (sheetName === deviceName) continue;
    if (!sheetName.toLowerCase().includes('tilt')) continue;

    const match = searchTiltSheet_(sheet, targetTime);
    if (match && match.timeDiff < bestDiff) {
      bestDiff = match.timeDiff;
      bestMatch = match;
    }
  }

  return bestMatch;
}

function searchTiltSheet_(sheet, targetTime) {
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return null;

  const headers = data[0];
  let timestampCol = -1;
  let gravityCol = -1;
  let colorCol = -1;

  for (let i = 0; i < headers.length; i++) {
    const header = headers[i].toString().toLowerCase();
    if (timestampCol === -1 && (header.includes('time') || header.includes('date'))) {
      timestampCol = i;
    }
    if (gravityCol === -1 && (header.includes('gravity') || header.includes('sg'))) {
      gravityCol = i;
    }
    if (colorCol === -1 && (header.includes('color') || header.includes('name'))) {
      colorCol = i;
    }
  }

  if (timestampCol === -1 || gravityCol === -1) {
    return null;
  }

  const targetTimeMs = targetTime.getTime();
  const windowMs = TIME_MATCH_WINDOW * 1000;
  let closestMatch = null;
  let closestDiff = Infinity;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const rowTime = new Date(row[timestampCol]);
    const rowTimeMs = rowTime.getTime();
    if (isNaN(rowTimeMs)) continue;

    const diff = Math.abs(targetTimeMs - rowTimeMs);
    if (diff <= windowMs && diff < closestDiff) {
      closestDiff = diff;
      closestMatch = {
        gravity: row[gravityCol],
        color: colorCol >= 0 ? row[colorCol] : '',
        timestamp: rowTime,
        timeDiff: diff / 1000
      };
    }
  }

  return closestMatch;
}

function testDoPost() {
  const secret = getUploadSecret_();
  if (!secret) {
    throw new Error('Set PHLOAT_UPLOAD_SECRET in Script Properties before running testDoPost');
  }
  const testData = {
    postData: {
      contents: JSON.stringify({
        token: secret,            // token in the body — GAS cannot read headers
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

function doGet(e) {
  try {
    verifyUploadToken_(e.parameter.token);   // token travels as a query parameter
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
