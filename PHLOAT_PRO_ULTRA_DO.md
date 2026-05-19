# pHloat Pro Ultra - Dissolved Oxygen & Distillery Edition

## Overview

**YES to both questions!**

1. ✅ **Dissolved Oxygen (DO) monitoring is EXTREMELY valuable** - especially for distilleries
2. ✅ **Same ESP32-S3 can handle it** - still have plenty of GPIO and processing power
3. ✅ **Distillery fermentations have different requirements** - we'll cover adaptations

---

## Why Dissolved Oxygen Matters

### For Brewing

**Critical during two phases:**

**1. Pre-fermentation (Oxygenation):**
- Yeast needs O₂ for healthy cell membrane production
- Target: 8-12 ppm DO at pitch
- Too little: Stuck fermentation, off-flavors
- Too much: Oxidation, shortened beer shelf life

**2. Post-fermentation:**
- Want ZERO dissolved oxygen
- DO causes staling, cardboard flavors
- Critical during packaging/transfer
- Must monitor to maintain quality

### For Distilling - EVEN MORE CRITICAL!

**Distillery fermentations are different:**

**Higher Gravities:**
- Distiller's wash: 1.080-1.120+ (vs beer 1.050-1.070)
- More stressed yeast
- More critical O₂ management
- Need precise oxygenation

**Faster Fermentations:**
- Often complete in 2-4 days (vs 5-14 for beer)
- Higher temperatures (25-35°C vs 15-22°C)
- More vigorous CO₂ production
- Real-time monitoring essential

**No Oxygen Tolerance:**
- Wine/spirits oxidize more readily than beer
- Affects final spirit quality
- Cannot hide behind hops
- Every ppm matters

**Economic Impact:**
- Distillery wash is expensive (grain costs)
- Stuck fermentation = lost money
- Can't afford to guess at O₂ levels
- ROI on DO sensor is immediate

### Specific Use Cases

**Distillery Applications:**

✅ **Rum production:**
- Monitor DO during molasses dilution
- Control oxygenation of high-gravity wash
- Prevent oxidation during fermentation
- Critical for flavor development

✅ **Whiskey production:**
- Grain mash oxygen pickup monitoring
- Yeast propagation O₂ levels
- Fermentation vessel DO tracking
- Prevents off-flavors in distillate

✅ **Vodka/Neutral spirits:**
- Minimize oxidation (affects purity)
- Maximize fermentation efficiency
- Monitor yeast health

✅ **Gin production:**
- Base spirit quality critical
- DO affects botanical extraction
- Monitor neutral grain spirit production

**Brewery Applications:**

✅ **High-gravity beers:**
- Imperial stouts, barleywines
- Need more O₂ at pitch
- Monitor throughout fermentation

✅ **Lagers:**
- Long, cold fermentations
- DO affects diacetyl production
- Critical during lagering

✅ **Packaging:**
- Monitor DO during transfers
- Canning/bottling line monitoring
- Shelf-life predictor

---

## Dissolved Oxygen Sensor Options

### Option 1: Atlas Scientific DO Sensor (Recommended)

**Atlas Scientific DO-1200 Dissolved Oxygen OEM Circuit**

**Specifications:**
- Same family as pH sensor you're using
- I²C interface (same as pH!)
- Range: 0.01 - 100+ mg/L (ppm)
- Accuracy: ±0.05 mg/L
- Response time: 90% in 60 seconds
- Power: 3.3V (same as pH)
- **Cost:** $300-350 (circuit + probe)

**Why This is Perfect:**

✅ **Same I²C bus as pH sensor** - easy integration
✅ **Same manufacturer** - consistent API
✅ **Food-grade probe** - sanitary tri-clamp mount
✅ **Temperature compensated** - built-in
✅ **Proven technology** - industry standard
✅ **Easy calibration** - air saturation or zero-DO solution

**Probe Options:**

1. **Consumer Grade DO Probe** ($200)
   - Good for homebrewing
   - 1-2 year lifespan
   - Adequate accuracy

2. **Lab Grade DO Probe** ($400)
   - Professional accuracy
   - 2-3 year lifespan
   - Better stability

3. **Industrial DO Probe** ($600+)
   - Commercial distillery grade
   - 3-5 year lifespan
   - Autoclavable

**Recommendation for Distillery:** Lab Grade minimum ($400 total for circuit + probe)

### Option 2: Optical DO Sensor (Alternative)

**PyroScience FireSting or Similar**

**Specifications:**
- Optical luminescence method (no membrane)
- More stable than electrochemical
- Longer lifespan (5+ years)
- More expensive ($800-1,500)
- USB or analog output

**Pros:**
- ✅ No consumables (no membrane)
- ✅ Longer calibration intervals
- ✅ More stable readings
- ✅ Less maintenance

**Cons:**
- ❌ More expensive initially
- ❌ May need USB host or ADC interface
- ❌ Less common in brewing

**Recommendation:** Atlas is better value for this project

### Option 3: Budget Optical DO Meter (~$150)

**Generic optical DO sensors (Amazon/AliExpress)**

**Pros:**
- ✅ Cheap ($100-150)
- ✅ USB output available

**Cons:**
- ❌ Unknown accuracy
- ❌ May not have temperature compensation
- ❌ Difficult I²C integration
- ❌ Poor documentation

**Recommendation:** Not worth the headache for Pro system

---

## ESP32-S3 - Still Perfect!

### GPIO Availability Check

**Currently Used:**
- GPIO 8, 9: I²C (pH sensor)
- GPIO 4: Pump 1 (acid)
- GPIO 5: Pump 2 (base)
- GPIO 6: DS18B20 (temperature)
- GPIO 7: SSR (heater)
- GPIO 10: Solenoid (cooling)

**Available:** 20+ GPIO pins!

**For DO Sensor:**
- **SAME I²C BUS!** (GPIO 8, 9)
- Multiple I²C devices on same bus
- Just different I²C address
- No additional pins needed!

**Atlas Scientific I²C Addresses:**
- pH OEM: 0x63 (default)
- DO OEM: 0x61 (default)
- **No conflict!**

### Processing Power Check

**Current Load:**
- pH PID: ~5% CPU
- Temperature PID: ~5% CPU
- BLE communication: ~5% CPU
- Sensor reading: ~2% CPU
- Data logging: ~3% CPU
- **Total: ~20% CPU**

**Adding DO:**
- DO sensor reading: ~2% CPU
- DO logging: ~1% CPU
- **New total: ~23% CPU**

**ESP32-S3 has dual cores @ 240MHz - plenty of headroom!**

### Memory Check

**Current Usage:**
- Code: ~400KB flash
- Variables: ~80KB RAM
- BLE stack: ~50KB RAM
- Profiles: ~100KB flash
- **Total: ~500KB flash, ~130KB RAM**

**Available:**
- 8MB flash (plenty!)
- 512KB RAM (plenty!)

**Adding DO:**
- Code: +20KB
- Variables: +5KB
- **No problem!**

---

## Hardware Integration

### Complete System Diagram

```
╔═══════════════════════════════════════════════════════════════╗
║       pHloat Pro Ultra - Complete Distillery Control          ║
╚═══════════════════════════════════════════════════════════════╝

                    Fermenter (Tri-Clamp Mounts)
                    ┌──────────────────────────┐
                    │  Fermentation Wash       │
                    │                          │
                    │  ╔══╗  ╔══╗  ╔══╗       │◄─── Glycol In
                    │  ║pH║  ║T°║  ║DO║       │
                    │  ║  ║  ║  ║  ║  ║       │
                    └──╚═▲╝──╚═▲╝──╚═▲╝───────┘◄─── Glycol Out
                        │     │     │
                  ──────┴─────┴─────┴───────────
                        │     │     │
                 ┌──────▼─────▼─────▼──────┐
                 │  pHloat Pro Ultra       │
                 │     (ESP32-S3)          │
                 │                         │
                 │  - pH Sensor            │
                 │  - DO Sensor    ◄─ SAME I²C BUS!
                 │  - Temp Sensor          │
                 │  - Dual PID Control     │
                 │  - Profile Management   │
                 │  - BLE Communication    │
                 └─────────┬───────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐   ┌────▼────┐   ┌──▼──────┐
       │ Dosing  │   │  Temp   │   │   O₂    │
       │ Pumps   │   │ Control │   │ Control │
       │(pH adj) │   │(heat/cool)  │(optional)│
       └─────────┘   └─────────┘   └─────────┘

            ⬇ BLE to Distillery Pi ⬇
            
         pH + Temp + DO + SG → Distillery Management
```

### Wiring - DO Sensor Addition

```
Atlas Scientific DO OEM Circuit
================================

Same I²C bus as pH sensor - just connects in parallel!

ESP32-S3              Atlas DO OEM
=========             ============
GPIO 8 (SDA)  ──┬──── SDA
                │
GPIO 9 (SCL)  ──┼──── SCL
                │
3.3V          ──┼──── VCC
                │
GND           ──┼──── GND
                │
                │     Atlas pH OEM
                │     =============
                ├──── SDA
                ├──── SCL
                ├──── VCC
                └──── GND

Both sensors share the I²C bus!
Different I²C addresses prevent conflicts.

DO Probe Connection:
====================
Atlas DO OEM has BNC connector
→ DO Probe (BNC)
→ Tri-clamp mount
→ Into fermenter wash
```

---

## Software Implementation

### Atlas DO Sensor Integration

```cpp
/*
 * Dissolved Oxygen Sensor Integration
 * Atlas Scientific DO-1200 OEM Circuit
 * 
 * Uses same I²C bus as pH sensor
 * Different I²C address: 0x61
 */

#define DO_SENSOR_ADDR 0x61
#define PH_SENSOR_ADDR 0x63  // Existing

// Calibration data for DO sensor
struct DOCalibration {
    float atmosphericPressure;  // mBar (for accurate calibration)
    float salinity;             // ppt (affects saturation)
    unsigned long lastCalibration;
    bool calibrated;
};

DOCalibration doCalibration = {
    1013.25,  // Standard atmospheric pressure (sea level)
    0.0,      // Fresh water (distilled water fermentation)
    0,
    false
};

// Initialize DO sensor
bool initDOSensor() {
    Wire.begin(I2C_SDA, I2C_SCL);
    
    // Test communication
    Wire.beginTransmission(DO_SENSOR_ADDR);
    byte error = Wire.endTransmission();
    
    if (error != 0) {
        Serial.println("DO sensor not found!");
        return false;
    }
    
    Serial.println("DO sensor initialized");
    
    // Set temperature compensation (from DS18B20)
    setDOTemperature(currentTemp);
    
    // Set salinity (usually 0 for distilling)
    setDOSalinity(0.0);
    
    return true;
}

// Read dissolved oxygen
float readDO() {
    Wire.beginTransmission(DO_SENSOR_ADDR);
    Wire.write('R');  // Read command (same as pH!)
    Wire.endTransmission();
    
    delay(600);  // DO sensor needs 600ms
    
    Wire.requestFrom(DO_SENSOR_ADDR, 20);
    
    byte code = Wire.read();
    if (code != 1) {  // 1 = success
        Serial.printf("DO read error: code %d\n", code);
        return -1.0;
    }
    
    char data[20];
    int i = 0;
    while (Wire.available() && i < 19) {
        data[i++] = Wire.read();
    }
    data[i] = '\0';
    
    float dissolvedO2 = atof(data);
    return dissolvedO2;  // Returns mg/L (ppm)
}

// Set temperature for compensation (call whenever temp changes)
void setDOTemperature(float tempC) {
    char cmd[20];
    sprintf(cmd, "T,%.2f", tempC);
    
    Wire.beginTransmission(DO_SENSOR_ADDR);
    Wire.write(cmd);
    Wire.endTransmission();
    
    delay(300);
}

// Set salinity (usually 0 for distilling, up to 50 for seawater)
void setDOSalinity(float salinity_ppt) {
    char cmd[20];
    sprintf(cmd, "S,%.1f", salinity_ppt);
    
    Wire.beginTransmission(DO_SENSOR_ADDR);
    Wire.write(cmd);
    Wire.endTransmission();
    
    delay(300);
}

// Calibrate DO sensor - Atmospheric (air saturation)
bool calibrateDOAtmospheric(float pressure_mbar) {
    // Sensor must be in air, not water!
    // Wait 5 minutes for membrane to equilibrate
    
    char cmd[20];
    sprintf(cmd, "Cal");  // Atmospheric calibration
    
    Wire.beginTransmission(DO_SENSOR_ADDR);
    Wire.write(cmd);
    Wire.endTransmission();
    
    delay(1300);  // Calibration takes longer
    
    Wire.requestFrom(DO_SENSOR_ADDR, 20);
    byte code = Wire.read();
    
    if (code == 1) {
        doCalibration.atmosphericPressure = pressure_mbar;
        doCalibration.lastCalibration = millis();
        doCalibration.calibrated = true;
        
        Serial.println("DO atmospheric calibration successful");
        return true;
    }
    
    Serial.println("DO calibration failed!");
    return false;
}

// Calibrate DO sensor - Zero (0 mg/L)
bool calibrateDOZero() {
    // Sensor must be in zero-DO solution
    // Use sodium sulfite solution
    
    Wire.beginTransmission(DO_SENSOR_ADDR);
    Wire.write("Cal,0");  // Zero calibration
    Wire.endTransmission();
    
    delay(1300);
    
    Wire.requestFrom(DO_SENSOR_ADDR, 20);
    byte code = Wire.read();
    
    if (code == 1) {
        Serial.println("DO zero calibration successful");
        return true;
    }
    
    Serial.println("DO zero calibration failed!");
    return false;
}

// Get percent saturation (useful metric)
float getDOSaturation() {
    // Calculate based on temperature and pressure
    // Saturation at 20°C, 1013mbar = ~9.1 mg/L
    
    float saturation = calculateDOSaturation(currentTemp, 
                                            doCalibration.atmosphericPressure);
    float percentSat = (currentDO / saturation) * 100.0;
    
    return percentSat;
}

float calculateDOSaturation(float tempC, float pressure_mbar) {
    // Henry's Law approximation
    // More accurate formula available in Atlas documentation
    
    float saturation_at_sealevel = 14.6 - (0.41 * tempC) + (0.0079 * tempC * tempC) 
                                   - (0.000084 * tempC * tempC * tempC);
    
    // Pressure correction
    float saturation = saturation_at_sealevel * (pressure_mbar / 1013.25);
    
    return saturation;
}
```

### Updated Main Loop with DO

```cpp
void loop() {
    unsigned long now = millis();
    static unsigned long lastControlUpdate = 0;
    static unsigned long lastDataLog = 0;
    static unsigned long lastDOUpdate = 0;
    
    // Read sensors (different intervals)
    
    // pH - every 60 seconds
    if (now - lastControlUpdate > 60000) {
        currentPH = readPH();
        currentTemp = readTemperature();
        
        // Update DO temperature compensation
        setDOTemperature(currentTemp);
    }
    
    // DO - every 30 seconds (can be more frequent)
    if (now - lastDOUpdate > 30000) {
        lastDOUpdate = now;
        currentDO = readDO();
        currentDOSaturation = getDOSaturation();
        
        Serial.printf("DO: %.2f mg/L (%.1f%% saturation)\n", 
                     currentDO, currentDOSaturation);
    }
    
    // Control loop - every 10 seconds
    if (now - lastControlUpdate > 10000) {
        lastControlUpdate = now;
        
        // Update BLE data (including DO now)
        updateBLEData();
        
        // Safety checks (including DO limits)
        if (!performSafetyChecks()) {
            emergencyShutdown();
            return;
        }
        
        // Get targets from profile
        if (replayMode) {
            unsigned long hoursFromPitch = (now - pitchTime) / 3600000;
            
            float targetPH = interpolateProfilePH(hoursFromPitch);
            float targetTemp = interpolateProfileTemp(hoursFromPitch);
            float targetDO = interpolateProfileDO(hoursFromPitch);
            
            pidController.setTarget(targetPH, 0.05, 0.05);
            tempController.setTarget(targetTemp);
            // DO is typically monitored, not controlled (see below)
            
            Serial.printf("Profile: T+%luh, pH %.2f, Temp %.1f°C, DO %.2f mg/L\n",
                         hoursFromPitch, targetPH, targetTemp, targetDO);
        }
        
        // pH Control
        if (autoMode && currentMode == MODE_AUTO_NORMAL) {
            performDosing(currentPH);
        }
        
        // Temperature Control
        if (tempControlEnabled) {
            tempController.calculate(currentTemp);
            applyTemperatureControl();
        }
        
        // DO Monitoring (typically not controlled during fermentation)
        checkDOLevels();
    }
    
    // Data logging - every minute
    if (now - lastDataLog > 60000) {
        lastDataLog = now;
        logData();  // Now includes DO
        
        if (learningMode) {
            recordProfilePoint();  // Now includes DO
        }
    }
    
    delay(100);
}
```

---

## DO Monitoring vs Control

### Why Not Control DO During Fermentation?

**Unlike pH and temperature, DO is typically MONITORED, not controlled during active fermentation:**

**Reasons:**

1. **Yeast consumes O₂ rapidly** - Within first 12 hours
2. **CO₂ production** - Drives out dissolved oxygen naturally
3. **Adding O₂ mid-fermentation** - Generally undesirable (creates off-flavors)
4. **Control is pre-fermentation** - Oxygenate wort/wash before pitch

**Exception:** Some distillery fermentations benefit from micro-oxygenation, but this is advanced.

### What DO Monitoring Tells You

**Early Fermentation (0-24 hours):**
```
DO Level     Meaning
========     =======
8-12 ppm     Optimal oxygenation - healthy start
5-8 ppm      Adequate - fermentation will proceed
2-5 ppm      Low - may have sluggish fermentation
< 2 ppm      Very low - risk of stuck fermentation
> 12 ppm     Over-oxygenated - oxidation risk
```

**Active Fermentation (24-72 hours):**
```
DO Level     Meaning
========     =======
< 0.5 ppm    Normal - yeast consumed O₂, CO₂ present
0.5-2 ppm    Unusual - check fermentation activity
> 2 ppm      Problem - fermentation may be stuck
```

**Post-Fermentation:**
```
DO Level     Meaning
========     =======
< 0.1 ppm    Excellent - minimal oxidation risk
0.1-0.5 ppm  Good - acceptable for spirits
0.5-1 ppm    Concerning - may affect quality
> 1 ppm      Bad - oxidation occurring
```

### Optional: DO Control Pre-Fermentation

**If you want to automate oxygenation:**

```cpp
/*
 * Pre-fermentation oxygenation control
 * Bubbles O₂ through wort/wash to target level
 * 
 * Hardware needed:
 * - O₂ regulator + diffusion stone
 * - Solenoid valve on O₂ line
 * - DO sensor (already have!)
 */

#define O2_SOLENOID_PIN 11
#define TARGET_DO 10.0  // mg/L

void oxygenateWash() {
    Serial.println("Starting oxygenation...");
    
    float startDO = readDO();
    unsigned long startTime = millis();
    
    while (currentDO < TARGET_DO) {
        // Open O₂ solenoid
        digitalWrite(O2_SOLENOID_PIN, HIGH);
        
        // Wait 10 seconds
        delay(10000);
        
        // Close solenoid
        digitalWrite(O2_SOLENOID_PIN, LOW);
        
        // Wait 20 seconds for mixing
        delay(20000);
        
        // Read DO
        currentDO = readDO();
        
        Serial.printf("DO: %.2f mg/L (target %.2f)\n", currentDO, TARGET_DO);
        
        // Safety timeout (5 minutes max)
        if (millis() - startTime > 300000) {
            Serial.println("Oxygenation timeout!");
            break;
        }
        
        // Safety check - don't over-oxygenate
        if (currentDO > TARGET_DO + 2.0) {
            Serial.println("DO target exceeded - stopping");
            break;
        }
    }
    
    digitalWrite(O2_SOLENOID_PIN, LOW);
    Serial.printf("Oxygenation complete: %.2f mg/L\n", currentDO);
}
```

---

## Distillery-Specific Adaptations

### Key Differences: Distillery vs Brewery

| Parameter | Brewery | Distillery | pHloat Pro Ultra Setting |
|-----------|---------|------------|--------------------------|
| **Starting Gravity** | 1.040-1.080 | 1.080-1.120+ | Update profile structure |
| **Target pH** | 4.4-4.6 | 4.0-4.8 (varies) | Wider acceptable range |
| **Fermentation Temp** | 15-22°C | 25-35°C | Higher temp PID tuning |
| **Fermentation Time** | 5-14 days | 2-4 days | Faster logging intervals |
| **DO at Pitch** | 8-10 ppm | 10-12 ppm | Higher target |
| **Final pH Importance** | Flavor | Critical for yield | Tighter control |
| **Temperature Swings** | Minimize | Some tolerated | Less critical |

### Code Adaptations for Distillery

```cpp
/*
 * Distillery-specific configuration
 */

// Distillery fermentation parameters
#define DISTILLERY_MODE true

#if DISTILLERY_MODE
    // Higher temperature targets
    #define DEFAULT_FERMENT_TEMP 30.0  // vs 18°C for beer
    #define TEMP_TOLERANCE 1.0         // vs 0.5°C for beer (less critical)
    
    // Different pH range
    #define DEFAULT_TARGET_PH 4.2      // vs 4.5 for beer
    #define PH_TOLERANCE 0.10          // vs 0.05 (wider range OK)
    
    // Higher DO at pitch
    #define TARGET_PITCH_DO 12.0       // vs 10.0 for beer
    
    // Faster logging (more activity)
    #define LOG_INTERVAL 30000         // 30 seconds vs 60 for beer
    
    // Faster fermentation profile
    #define TYPICAL_FERMENT_TIME 72    // 72 hours vs 168 for beer
    
    // Higher gravity handling
    #define MAX_STARTING_GRAVITY 1.120  // vs 1.080 for beer
    
#else
    // Brewery mode (existing values)
    #define DEFAULT_FERMENT_TEMP 18.0
    #define TEMP_TOLERANCE 0.5
    #define DEFAULT_TARGET_PH 4.5
    #define PH_TOLERANCE 0.05
    #define TARGET_PITCH_DO 10.0
    #define LOG_INTERVAL 60000
    #define TYPICAL_FERMENT_TIME 168
    #define MAX_STARTING_GRAVITY 1.080
#endif

// Distillery wash profile example
FermentationProfile createRumWashProfile() {
    FermentationProfile profile;
    
    strcpy(profile.name, "Rum Wash - Molasses");
    strcpy(profile.style, "Rum");
    strcpy(profile.yeastStrain, "DADY - Distillers Active Dry Yeast");
    
    profile.pitchTemp = 30.0;
    profile.primaryTemp = 30.0;
    profile.tempTolerance = 1.0;
    profile.phTolerance = 0.10;
    
    int idx = 0;
    
    // Pitch - T+0h
    profile.points[idx++] = {0, 4.8, 1.095, 30.0, 12.0, "Pitch - high DO"};
    
    // Lag phase - T+4h
    profile.points[idx++] = {4, 4.7, 1.094, 30.0, 2.0, "Lag ending"};
    
    // Very active - T+12h
    profile.points[idx++] = {12, 4.4, 1.080, 31.0, 0.2, "Vigorous"};
    
    // Peak - T+24h
    profile.points[idx++] = {24, 4.2, 1.055, 32.0, 0.1, "Peak"};
    
    // Slowing - T+36h
    profile.points[idx++] = {36, 4.1, 1.030, 31.0, 0.1, "Slowing"};
    
    // Nearly done - T+48h
    profile.points[idx++] = {48, 4.0, 1.015, 30.0, 0.05, "Finishing"};
    
    // Complete - T+60h
    profile.points[idx++] = {60, 4.0, 1.008, 28.0, 0.05, "Complete"};
    
    // Cool for distillation - T+72h
    profile.points[idx++] = {72, 4.0, 1.006, 25.0, 0.05, "Ready to distill"};
    
    profile.numPoints = idx;
    profile.totalDuration = 72;
    
    return profile;
}
```

### Rum-Specific Considerations

**Molasses fermentation:**
- High sugar content (1.090-1.110)
- Needs more nutrients
- pH drops quickly
- Very vigorous fermentation
- Critical DO at start

**pH Management:**
```cpp
// Rum wash - pH drops fast initially
// Then stabilizes
// May need buffering rather than continuous adjustment

void checkRumWashPH() {
    if (hoursFromPitch < 12) {
        // Early fermentation - pH dropping is normal
        // Only intervene if drops below 3.8
        if (currentPH < 3.8) {
            // Dose base to bring back to 4.0
            Serial.println("pH too low for yeast health!");
        }
    } else {
        // Later fermentation - maintain 4.0-4.2
        // Normal pH control
    }
}
```

### Whiskey-Specific Considerations

**Grain mash:**
- Starch conversion affects pH
- Monitor DO during transfer from mash to fermenter
- Cooler fermentation (25-28°C)
- Longer than rum (3-5 days)

```cpp
FermentationProfile createWhiskeyWashProfile() {
    FermentationProfile profile;
    
    strcpy(profile.name, "Bourbon Mash");
    strcpy(profile.style, "Whiskey");
    strcpy(profile.yeastStrain, "Whiskey Yeast");
    
    profile.pitchTemp = 25.0;
    profile.primaryTemp = 26.0;
    
    int idx = 0;
    profile.points[idx++] = {0, 5.2, 1.075, 25.0, 10.0, "Pitch"};
    profile.points[idx++] = {12, 4.9, 1.070, 26.0, 0.5, "Active"};
    profile.points[idx++] = {24, 4.6, 1.058, 27.0, 0.1, "Vigorous"};
    profile.points[idx++] = {48, 4.3, 1.032, 26.0, 0.1, "Slowing"};
    profile.points[idx++] = {72, 4.2, 1.015, 26.0, 0.05, "Finishing"};
    profile.points[idx++] = {96, 4.2, 1.010, 25.0, 0.05, "Complete"};
    
    profile.numPoints = idx;
    profile.totalDuration = 96;
    
    return profile;
}
```

---

## Enhanced Profile Structure with DO

```cpp
struct FermentationPoint {
    unsigned long timeOffset;   // Hours from pitch
    float pH;
    float specificGravity;
    float temperature;          // °C
    float dissolvedOxygen;      // mg/L (NEW!)
    char notes[64];
};

// Save/load profiles with DO data
void saveProfileToSPIFFS(FermentationProfile* profile) {
    File file = SPIFFS.open(String("/profiles/") + profile->name + ".dat", "w");
    if (!file) {
        Serial.println("Failed to open profile for writing");
        return;
    }
    
    // Write profile structure (now includes DO!)
    file.write((uint8_t*)profile, sizeof(FermentationProfile));
    file.close();
    
    Serial.printf("Saved profile: %s (%d points)\n", 
                  profile->name, profile->numPoints);
}
```

---

## Updated BLE Data Structure

```cpp
// Additional UUID for DO
#define CHARACTERISTIC_DO_UUID "12345678-1234-1234-1234-123456789ac4"
#define CHARACTERISTIC_DO_SAT_UUID "12345678-1234-1234-1234-123456789ac5"

void setupBLE() {
    // ... (existing setup)
    
    pDOCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_DO_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pDOCharacteristic->addDescriptor(new BLE2902());
    
    pDOSatCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_DO_SAT_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pDOSatCharacteristic->addDescriptor(new BLE2902());
    
    // ... (rest of setup)
}

void updateBLEData() {
    if (!deviceConnected) return;
    
    // ... (existing updates for pH, temp, etc.)
    
    // Update DO
    char doStr[16];
    sprintf(doStr, "%.2f", currentDO);
    pDOCharacteristic->setValue(doStr);
    pDOCharacteristic->notify();
    
    // Update DO saturation percentage
    char satStr[16];
    sprintf(satStr, "%.1f", currentDOSaturation);
    pDOSatCharacteristic->setValue(satStr);
    pDOSatCharacteristic->notify();
}
```

---

## Cost Analysis

### pHloat Pro Ultra - Complete System

| Component | Cost |
|-----------|------|
| **Core System** | |
| ESP32-S3 | $12 |
| Atlas pH OEM + probe | $210 |
| Atlas DO OEM + probe | $500 (lab grade) |
| DS18B20 temp sensor | $5 |
| **Control Hardware** | |
| Dosing pumps (2×) | $60 |
| Motor driver | $5 |
| SSR (heater) | $12 |
| Solenoid (cooling) | $25 |
| Heating element | $30 |
| **Power & Misc** | |
| Power supply | $15 |
| Buck converter | $5 |
| Enclosures | $40 |
| Tri-clamp fittings (3×) | $90 |
| Wiring, connectors | $30 |
| Tubing, fittings | $25 |
| **TOTAL** | **~$1,064** |

**Plus cooling system:**
- Glycol chiller: +$500
- OR Chamber: +$175
- OR DIY glycol: +$250

**Complete Ultra System: $1,239-1,564**

### ROI for Distillery

**Cost of one stuck fermentation:**
- 100 gallons wash @ $2/gallon grain = $200
- Labor and energy = $100
- Lost production time = $200
- **Total loss: $500**

**System pays for itself after preventing 3 stuck fermentations!**

**For commercial distillery:**
- Prevents 1-2 stuck fermentations per year
- Better yield optimization (2-3% improvement)
- More consistent product quality
- **ROI: 6-12 months**

---

## Hardware Summary

### Complete Bill of Materials

**Sensors (All Tri-Clamp Mounted):**
1. Atlas Scientific pH OEM + Lab Probe: $210
2. Atlas Scientific DO OEM + Lab Probe: $500
3. DS18B20 Temperature Probe: $5

**Control Outputs:**
1. 2× Peristaltic Pumps (pH adjustment): $60
2. SSR + Heating Element: $42
3. Solenoid Valve (cooling): $25
4. Optional: O₂ Solenoid (pre-fermentation): $25

**Electronics:**
1. ESP32-S3 DevKit: $12
2. L298N Motor Driver: $5
3. Buck Converter: $5
4. Power Supply (12V 3A): $15

**Total Core: ~$904**

**Very reasonable for a complete distillery fermentation control system!**

---

## Summary

### Questions Answered

**Q1: Would adding DO sensors make a difference?**
✅ **YES! Huge difference, especially for distilleries:**
- Monitor oxygenation at pitch (critical for high-gravity washes)
- Track fermentation health in real-time
- Prevent oxidation post-fermentation
- Optimize yield and quality
- Essential for professional distillery operations

**Q2: Can it run on same ESP32-S3?**
✅ **YES! Same hardware, same I²C bus:**
- DO sensor just connects to existing I²C bus
- Different address than pH (0x61 vs 0x63)
- No additional pins needed
- Plenty of processing power remaining
- Still 15+ free GPIO for future expansion

**Q3: Differences for distillery vs brewery?**
✅ **YES! Important differences:**
- Higher gravity fermentations (1.080-1.120+)
- Higher temperatures (25-35°C vs 15-22°C)
- Faster fermentations (2-4 days vs 5-14 days)
- pH range different (4.0-4.8 vs 4.4-4.6)
- DO more critical (higher pitch levels needed)
- Economic impact higher (grain costs)

### What You Get

**pHloat Pro Ultra - Complete System:**
- ✅ pH monitoring and control
- ✅ Temperature monitoring and control
- ✅ Dissolved oxygen monitoring
- ✅ Profile learning and replay (pH + Temp + DO + SG)
- ✅ Dual PID controllers
- ✅ BLE communication
- ✅ Distillery-optimized algorithms
- ✅ Complete safety systems

**All on one ESP32-S3!**

### Recommended Configurations

**For Serious Homebrewer:**
- pHloat Pro (pH + Temp): $650-1,000
- Skip DO (not essential for beer)

**For Craft Distillery:**
- pHloat Pro Ultra (pH + Temp + DO): $1,200-1,500
- DO is worth it for wash quality
- ROI in 6-12 months

**For Commercial Distillery:**
- pHloat Pro Ultra with lab-grade sensors
- Multiple units (one per fermenter)
- Cost: $1,500 per fermenter
- vs commercial: $5,000-10,000 per fermenter
- Massive savings at scale!

---

**Complete documentation now includes DO sensor integration and distillery adaptations!** 🥃
