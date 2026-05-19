# pHloat Pro - Automated pH Control System

## Overview

The **pHloat Pro** is an advanced fermentation control system that:
- Mounts externally via tri-clamp fitting (permanent installation)
- Communicates directly with Tilt Pi via BLE (no relay needed)
- Actively controls pH via peristaltic pumps (acid/base dosing)
- Uses PID control for precise, minimal intervention
- Learns from previous fermentations to recreate pH/SG profiles

This is a **professional-grade system** for serious brewers who want reproducible results.

---

## Hardware Platform Selection

### Recommended: ESP32-S3 (Same as Basic Version)

**Best Choice: ESP32-S3-WROOM-1 Module**

**Why ESP32-S3 is Perfect:**

✅ **Security Features:**
- RSA-3072 accelerator
- AES-128/256 encryption
- Secure boot
- Flash encryption
- Digital signature verification

✅ **BLE 5.0 Support:**
- Built-in Bluetooth LE
- Long range mode
- Better coexistence with WiFi
- Lower power consumption

✅ **Processing Power:**
- Dual-core Xtensa LX7 @ 240MHz
- 512KB SRAM (plenty for PID calculations)
- Floating point unit (great for PID math)
- 8MB+ flash for data logging

✅ **Peripherals:**
- Multiple I2C buses (pH sensor + other sensors)
- Hardware PWM for pump control
- ADC for flow sensors
- RTC for timing

✅ **Development:**
- Arduino IDE support
- ESP-IDF for advanced features
- Active community
- Extensive libraries

**Recommended Dev Board:**
- **ESP32-S3-DevKitC-1** (~$10-15)
  - USB-C programming
  - All GPIOs broken out
  - Onboard voltage regulator
  - Reset and boot buttons

### Alternative: ESP32-C3 (Budget Option)

**ESP32-C3-WROOM-02**

**Pros:**
- RISC-V processor (modern architecture)
- BLE 5.0
- Lower cost ($5-8)
- Good security features
- Lower power

**Cons:**
- Single core (vs dual core)
- Less RAM (400KB vs 512KB)
- Smaller community

**Use if:** Budget is critical, but ESP32-S3 is better overall.

### NOT Recommended: ESP32 Classic

**Why avoid original ESP32:**
- ❌ Older BLE 4.2 (not 5.0)
- ❌ Less secure
- ❌ Lower performance
- ❌ Being phased out

---

## System Architecture

```
╔═══════════════════════════════════════════════════════════════╗
║                    pHloat Pro System                          ║
╚═══════════════════════════════════════════════════════════════╝

                    Fermenter (Tri-Clamp Mount)
                    ┌─────────────────────────┐
                    │                         │
                    │   Fermentation Beer     │
                    │                         │
                    │         ╔═══╗           │
                    │         ║ pH║           │
                    │         ║   ║           │
                    └─────────╚═▲═╝───────────┘
                              │ │
                    Tri-Clamp │ │ Probe
                    ──────────┴─┴─────────────
                              │
                       ┌──────▼──────┐
                       │ pHloat Pro  │
                       │  Controller │
                       │ (ESP32-S3)  │
                       │             │
                       │ - pH Sensor │
                       │ - BLE Radio │
                       │ - PID Logic │
                       │ - 2× Pumps  │
                       └──┬─────┬────┘
                          │     │
              ┌───────────┘     └───────────┐
              │                             │
       ┌──────▼──────┐             ┌───────▼──────┐
       │ Peristaltic │             │ Peristaltic  │
       │  Pump #1    │             │  Pump #2     │
       │  (Acid)     │             │  (Base)      │
       └──────┬──────┘             └───────┬──────┘
              │                            │
       ┌──────▼──────┐             ┌──────▼──────┐
       │  pH Down    │             │   pH Up     │
       │  Solution   │             │  Solution   │
       │  Reservoir  │             │  Reservoir  │
       └─────────────┘             └─────────────┘

                    ⬇ BLE Communication ⬇
                    
                    ┌─────────────────┐
                    │  Raspberry Pi   │
                    │   (Tilt Pi)     │
                    │                 │
                    │ - Receives pH   │
                    │ - Logs dosing   │
                    │ - Profile mgmt  │
                    └────────┬────────┘
                             │
                             ⬇
                    ┌────────▼────────┐
                    │ Google Sheets   │
                    │                 │
                    │ pH + SG + Dose  │
                    └─────────────────┘
```

---

## Bill of Materials (pHloat Pro)

### Core Components

| Item | Specification | Qty | Cost | Source |
|------|--------------|-----|------|--------|
| **ESP32-S3 DevKit** | ESP32-S3-DevKitC-1 | 1 | $12 | Amazon, Adafruit |
| **Atlas Scientific pH OEM** | I2C, 3.3V | 1 | $60 | Atlas Scientific |
| **pH Probe** | Lab-grade, Tri-clamp mount | 1 | $150 | Atlas, Mettler Toledo |
| **Tri-clamp Fitting** | 1.5" TC, probe adapter | 1 | $30 | Homebrew supply |
| **Peristaltic Pump (2×)** | 12V, 0-100ml/min | 2 | $30 ea | Amazon, eBay |
| **Motor Driver** | L298N or TB6612 | 1 | $5 | Amazon |
| **Power Supply** | 12V 2A (for pumps) | 1 | $12 | Amazon |
| **Buck Converter** | 12V→5V for ESP32 | 1 | $5 | Amazon |
| **Enclosure** | IP65, ~200×150×75mm | 1 | $25 | Hammond, Polycase |
| **Tubing** | Food-grade silicone, 3/16" ID | 10 ft | $15 | Amazon |
| **Check Valves** | 1/4" barb, inline | 2 | $10 | Amazon |
| **Dosing Containers** | 1L HDPE bottles | 2 | $10 | Amazon |
| **Connectors & Wire** | Misc | - | $20 | - |

**Total Hardware Cost: ~$385-400**

Compare to commercial systems: $2,000-5,000+ 🎉

### Optional Upgrades

| Item | Purpose | Cost |
|------|---------|------|
| Flow sensors (2×) | Verify dosing accuracy | $10 |
| Temperature sensor | Temp compensation | $5 |
| Pressure sensor | Fermentation activity | $15 |
| OLED display | Local status display | $8 |
| External antenna | Better BLE range | $5 |

---

## Detailed Component Selection

### 1. pH Probe (Critical Component)

**Commercial fermentation requires industrial-grade probe!**

**Option A: Atlas Scientific Lab-Grade pH Probe with Tri-Clamp** ($150-200)
- ✅ Specifically designed for fermentation
- ✅ Tri-clamp adapter available
- ✅ Temperature compensation
- ✅ Refillable electrolyte
- ✅ 1-2 year lifespan
- ✅ Excellent accuracy (±0.01 pH)

**Option B: Mettler Toledo InPro Series** ($300-500)
- ✅ Professional brewing standard
- ✅ Autoclavable
- ✅ Very long lifespan (3+ years)
- ✅ Best accuracy (±0.005 pH)
- ✅ Tri-clamp mount standard

**Option C: Budget Generic Tri-Clamp pH Probe** ($80-120)
- ✅ Affordable
- ❌ Shorter lifespan
- ❌ Less accurate
- ❌ May drift more

**Recommendation:** Start with Atlas ($150), upgrade to Mettler Toledo if scaling up.

**Tri-Clamp Installation:**
- Standard 1.5" tri-clamp ferrule
- Food-grade gasket (EPDM or silicone)
- Must maintain sterile seal
- Consider CIP (Clean-In-Place) compatible probe

### 2. Peristaltic Pumps

**Why Peristaltic?**
- ✅ Self-priming
- ✅ No contamination (fluid only touches tubing)
- ✅ Accurate dosing
- ✅ Reversible
- ✅ Easy to clean (replace tubing)

**Recommended: Kamoer KCP-PRO** ($30-40)
- 12V DC motor
- 0.5-100 ml/min flow rate
- PWM speed control
- Stepper motor for precision
- Food-grade tubing

**Alternative: Generic DC Peristaltic** ($15-25)
- 12V DC motor
- Simple on/off control
- Less precise but adequate
- Cheap replacement if failed

**Specifications Needed:**
- Voltage: 12V DC
- Flow rate: 10-100 ml/min
- Tubing: Food-grade silicone
- Control: PWM or on/off

### 3. Motor Driver

**L298N Dual H-Bridge** ($5)
- ✅ Can drive 2 pumps
- ✅ PWM speed control
- ✅ Direction control (if needed)
- ✅ Very common, well-documented
- ✅ Handles 2A per channel

**Alternative: TB6612FNG** ($8)
- ✅ More efficient
- ✅ Smaller size
- ❌ Lower current (1.2A per channel)
- Better if using smaller pumps

### 4. Power Supply

**12V 2A+ Wall Adapter**
- Must provide enough current for both pumps
- Pumps: ~500mA each = 1A total
- Add 50% headroom = 1.5A minimum
- Recommend 2A for safety

**Buck Converter (12V → 5V):**
- Powers ESP32-S3
- LM2596 or similar
- Adjustable output
- ~1A capacity

---

## Wiring Diagram

```
╔═══════════════════════════════════════════════════════════════╗
║              pHloat Pro Complete Wiring Diagram               ║
╚═══════════════════════════════════════════════════════════════╝

                    ┌──────────────┐
                    │  12V 2A PSU  │
                    └───┬──────┬───┘
                        │      │
                   12V  │      │  GND
                        │      │
        ┌───────────────┼──────┼────────────────┐
        │               │      │                │
        │    ┌──────────▼──────▼──────┐         │
        │    │   Buck Converter        │         │
        │    │   (12V → 5V @ 1A)       │         │
        │    └──────────┬──────┬───────┘         │
        │               │      │                 │
        │          5V   │      │  GND            │
        │               │      │                 │
        │    ┌──────────▼──────▼───────────┐    │
        │    │      ESP32-S3               │    │
        │    │                             │    │
        │    │  GPIO 8 (SDA) ──┐           │    │
        │    │  GPIO 9 (SCL) ──┼──┐        │    │
        │    │  3.3V       ────┼──┼──┐     │    │
        │    │  GND        ────┼──┼──┼──┐  │    │
        │    │                 │  │  │  │  │    │
        │    │  GPIO 4 (PUMP1)─┼──┼──┼──┼──┼─────────┐
        │    │  GPIO 5 (PUMP2)─┼──┼──┼──┼──┼──────┐  │
        │    └─────────────────┼──┼──┼──┼──┘      │  │
        │                      │  │  │  │         │  │
        │         ┌────────────▼──▼──▼──▼───┐     │  │
        │         │  Atlas pH OEM Circuit   │     │  │
        │         │  SDA SCL VCC GND        │     │  │
        │         └────────┬─────────────┘  │     │  │
        │                  │ BNC             │     │  │
        │                  │                 │     │  │
        │            ┌─────▼──────┐          │     │  │
        │            │  pH Probe  │          │     │  │
        │            │ (Tri-Clamp)│          │     │  │
        │            └────────────┘          │     │  │
        │                                    │     │  │
        │         ┌──────────────────────────┼─────┼──┼──┐
        │         │    L298N Motor Driver    │     │  │  │
        │         │                          │     │  │  │
        │    12V  │  IN1 (Pump1) ◄───────────┘     │  │  │
        │    ─────┤  IN2 (Pump1 GND)               │  │  │
        │         │  IN3 (Pump2) ◄─────────────────┘  │  │
        │    GND  │  IN4 (Pump2 GND)                  │  │
        │    ─────┤                                   │  │
        │         │  OUT1 ──────────────────────┐     │  │
        │         │  OUT2 ──────────────────┐   │     │  │
        │         │  OUT3 ───────────────┐  │   │     │  │
        │         │  OUT4 ────────────┐  │  │   │     │  │
        │         └───────────────────┼──┼──┼───┼─────┘  │
        │                             │  │  │   │        │
        │                    ┌────────▼──▼──▼───▼──┐     │
        │                    │   Peristaltic        │     │
        │                    │   Pump #1 (Acid)     │     │
        │                    └──────────┬───────────┘     │
        │                               │                 │
        │                        ┌──────▼───────┐         │
        │                        │  Check Valve │         │
        │                        └──────┬───────┘         │
        │                               │                 │
        │                        ┌──────▼───────┐         │
        │                        │   Tubing to  │         │
        │                        │   Fermenter  │         │
        │                        └──────────────┘         │
        │                                                 │
        │                    ┌─────────────────────┐      │
        │                    │   Peristaltic       │      │
        │                    │   Pump #2 (Base) ◄──┘      │
        │                    └──────────┬──────────┘      │
        │                               │                 │
        │                        ┌──────▼───────┐         │
        │                        │  Check Valve │         │
        │                        └──────┬───────┘         │
        │                               │                 │
        │                        ┌──────▼───────┐         │
        │                        │   Tubing to  │         │
        │                        │   Fermenter  │         │
        │                        └──────────────┘         │
        └─────────────────────────────────────────────────┘

BLE Communication:
    ESP32-S3  ◄─────────► Raspberry Pi (Tilt Pi)
              (Wireless)
```

---

## PID Control Implementation

### Why PID Control?

**Goal:** Maintain pH with minimal intervention to avoid flavor impact.

**PID = Proportional + Integral + Derivative**

- **P (Proportional):** React to current error
  - Large error → Large correction
  - Small error → Small correction

- **I (Integral):** Eliminate steady-state error
  - Accumulates error over time
  - Fixes persistent offset

- **D (Derivative):** Dampen oscillations
  - Predicts future error based on rate of change
  - Prevents overshooting

### PID Tuning for pH Control

**Challenges with pH control:**
- Non-linear response (pH scale is logarithmic)
- Biological variability (yeast activity changes)
- Time delays (mixing takes time)
- Temperature effects

**Starting Parameters (Conservative):**
```cpp
// PID Gains (tune for your system)
float Kp = 2.0;   // Proportional gain
float Ki = 0.5;   // Integral gain  
float Kd = 1.0;   // Derivative gain

// These are STARTING values - tune experimentally!
```

### PID Algorithm Implementation

```cpp
/*
 * PID Controller for pH Control
 * 
 * Calculates pump dosing volume based on pH error
 * Uses clamping to prevent windup
 * Includes deadband to minimize interventions
 */

class PHController {
private:
    // PID gains
    float Kp = 2.0;
    float Ki = 0.5;
    float Kd = 1.0;
    
    // PID state
    float integralError = 0;
    float lastError = 0;
    unsigned long lastTime = 0;
    
    // Limits
    float maxIntegral = 10.0;    // Anti-windup
    float maxOutput = 100.0;     // Max dose (ml)
    float minOutput = 0.1;       // Min dose (ml)
    
    // Deadband (don't correct small errors)
    float deadband = 0.02;       // ±0.02 pH
    
    // Target range
    float targetPH = 4.5;
    float toleranceLow = 0.05;   // -0.05 pH
    float toleranceHigh = 0.05;  // +0.05 pH

public:
    // Set PID gains
    void setGains(float p, float i, float d) {
        Kp = p;
        Ki = i;
        Kd = d;
    }
    
    // Set target pH and tolerance
    void setTarget(float target, float tolLow, float tolHigh) {
        targetPH = target;
        toleranceLow = tolLow;
        toleranceHigh = tolHigh;
    }
    
    // Calculate dose needed
    float calculateDose(float currentPH) {
        unsigned long now = millis();
        float dt = (now - lastTime) / 1000.0;  // Time in seconds
        
        if (dt < 1.0) return 0;  // Too soon to recalculate
        
        // Calculate error
        float error = targetPH - currentPH;
        
        // Apply deadband (don't correct tiny errors)
        if (abs(error) < deadband) {
            lastTime = now;
            return 0;  // Within acceptable range
        }
        
        // Proportional term
        float P = Kp * error;
        
        // Integral term (with anti-windup clamping)
        integralError += error * dt;
        if (integralError > maxIntegral) integralError = maxIntegral;
        if (integralError < -maxIntegral) integralError = -maxIntegral;
        float I = Ki * integralError;
        
        // Derivative term
        float D = 0;
        if (dt > 0) {
            D = Kd * (error - lastError) / dt;
        }
        
        // Calculate output
        float output = P + I + D;
        
        // Clamp output to safe limits
        if (output > maxOutput) output = maxOutput;
        if (output < -maxOutput) output = -maxOutput;
        
        // Ignore very small outputs
        if (abs(output) < minOutput) output = 0;
        
        // Update state
        lastError = error;
        lastTime = now;
        
        // Return dose volume (ml)
        // Positive = acid needed (pH too high)
        // Negative = base needed (pH too low)
        return output;
    }
    
    // Reset controller (call when changing fermentation)
    void reset() {
        integralError = 0;
        lastError = 0;
        lastTime = millis();
    }
};

// Global instance
PHController pidController;
```

### Dosing Logic

```cpp
void performDosing(float currentPH) {
    // Get dose from PID controller
    float dose = pidController.calculateDose(currentPH);
    
    if (dose == 0) {
        // No action needed
        return;
    }
    
    // Log dosing event
    logDosing(dose, currentPH);
    
    if (dose > 0) {
        // pH too high - dose acid (pH down)
        doseAcid(dose);
        Serial.printf("Dosing ACID: %.2f ml (pH %.2f → target %.2f)\n", 
                      dose, currentPH, pidController.targetPH);
    } else {
        // pH too low - dose base (pH up)
        doseBase(abs(dose));
        Serial.printf("Dosing BASE: %.2f ml (pH %.2f → target %.2f)\n", 
                      abs(dose), currentPH, pidController.targetPH);
    }
    
    // Wait for mixing (30-60 seconds)
    delay(45000);
    
    // Re-measure pH to verify
    float newPH = readPH();
    Serial.printf("pH after dosing: %.2f\n", newPH);
}

void doseAcid(float volume_ml) {
    // Calculate pump run time
    // Assume pump flow rate: 10 ml/min
    float pumpRate = 10.0;  // ml/min
    float timeSeconds = (volume_ml / pumpRate) * 60.0;
    
    // Safety limit
    if (timeSeconds > 30) {
        Serial.println("WARNING: Dose time too long, limiting to 30s");
        timeSeconds = 30;
    }
    
    // Activate pump
    digitalWrite(PUMP_ACID_PIN, HIGH);
    delay(timeSeconds * 1000);
    digitalWrite(PUMP_ACID_PIN, LOW);
    
    // Log actual volume
    totalAcidDosed += volume_ml;
}

void doseBase(float volume_ml) {
    // Calculate pump run time
    float pumpRate = 10.0;  // ml/min
    float timeSeconds = (volume_ml / pumpRate) * 60.0;
    
    // Safety limit
    if (timeSeconds > 30) {
        Serial.println("WARNING: Dose time too long, limiting to 30s");
        timeSeconds = 30;
    }
    
    // Activate pump
    digitalWrite(PUMP_BASE_PIN, HIGH);
    delay(timeSeconds * 1000);
    digitalWrite(PUMP_BASE_PIN, LOW);
    
    // Log actual volume
    totalBaseDosed += volume_ml;
}
```

### PID Tuning Procedure

**Step 1: Start with P-only control**
```cpp
Kp = 2.0
Ki = 0.0
Kd = 0.0
```
- Increase Kp until system oscillates
- Reduce by 50%

**Step 2: Add integral**
```cpp
Ki = Kp / 10.0  // Start here
```
- Increase Ki until steady-state error eliminated
- Watch for instability

**Step 3: Add derivative**
```cpp
Kd = Kp * 0.5  // Start here
```
- Increase Kd to dampen oscillations
- Don't overdo it (amplifies noise)

**Expected tuning ranges for fermentation:**
- Kp: 1.0 - 5.0
- Ki: 0.1 - 1.0
- Kd: 0.5 - 2.0

**Auto-tuning option:** Implement Ziegler-Nichols method for automatic tuning.

---

## Fermentation Profile Recreation

### Concept: pH/SG Trajectory Matching

**Goal:** Reproduce a successful fermentation by following its pH and SG profile over time.

**Data Structure:**
```cpp
struct FermentationPoint {
    unsigned long timeOffset;  // Hours from pitch
    float pH;
    float specificGravity;
    float temperature;
};

struct FermentationProfile {
    char name[32];
    char style[32];  // "IPA", "Stout", etc.
    FermentationPoint points[100];
    int numPoints;
    unsigned long totalDuration;  // Hours
};
```

### Profile Learning Mode

```cpp
/*
 * Learn mode: Record pH/SG trajectory for future replication
 */

FermentationProfile currentProfile;
int profileIndex = 0;

void recordProfilePoint() {
    if (profileIndex >= 100) return;  // Profile full
    
    unsigned long hoursFromPitch = (millis() - pitchTime) / 3600000;
    
    FermentationPoint point;
    point.timeOffset = hoursFromPitch;
    point.pH = currentPH;
    point.specificGravity = currentSG;  // From Tilt via BLE
    point.temperature = currentTemp;
    
    currentProfile.points[profileIndex++] = point;
    currentProfile.numPoints = profileIndex;
    
    // Save to SPIFFS
    saveProfile(&currentProfile);
    
    Serial.printf("Profile point recorded: T+%lu hrs, pH %.2f, SG %.4f\n",
                  hoursFromPitch, point.pH, point.specificGravity);
}
```

### Profile Replay Mode

```cpp
/*
 * Replay mode: Follow a saved profile
 */

FermentationProfile targetProfile;
bool replayMode = false;

void loadProfile(const char* profileName) {
    // Load from SPIFFS
    File file = SPIFFS.open(String("/profiles/") + profileName + ".dat", "r");
    if (!file) {
        Serial.println("Profile not found!");
        return;
    }
    
    file.read((uint8_t*)&targetProfile, sizeof(FermentationProfile));
    file.close();
    
    replayMode = true;
    Serial.printf("Loaded profile: %s (%s)\n", 
                  targetProfile.name, targetProfile.style);
    Serial.printf("Duration: %lu hours, %d points\n",
                  targetProfile.totalDuration, targetProfile.numPoints);
}

void followProfile() {
    if (!replayMode) return;
    
    unsigned long hoursFromPitch = (millis() - pitchTime) / 3600000;
    
    // Find target pH for current time
    float targetPH = interpolateProfilePH(hoursFromPitch);
    float targetSG = interpolateProfileSG(hoursFromPitch);
    
    // Set PID target
    pidController.setTarget(targetPH, 0.05, 0.05);
    
    // Log deviation from profile
    float phError = abs(currentPH - targetPH);
    float sgError = abs(currentSG - targetSG);
    
    Serial.printf("Profile tracking: T+%lu hrs\n", hoursFromPitch);
    Serial.printf("  Target pH: %.2f, Actual: %.2f, Error: %.3f\n", 
                  targetPH, currentPH, phError);
    Serial.printf("  Target SG: %.4f, Actual: %.4f, Error: %.4f\n",
                  targetSG, currentSG, sgError);
    
    // Alert if significant deviation
    if (phError > 0.15 || sgError > 0.005) {
        Serial.println("WARNING: Significant deviation from profile!");
        sendBLEAlert("Profile deviation detected");
    }
}

float interpolateProfilePH(unsigned long currentHours) {
    // Find two nearest points
    for (int i = 0; i < targetProfile.numPoints - 1; i++) {
        if (currentHours >= targetProfile.points[i].timeOffset &&
            currentHours <= targetProfile.points[i+1].timeOffset) {
            
            // Linear interpolation between points
            float t1 = targetProfile.points[i].timeOffset;
            float t2 = targetProfile.points[i+1].timeOffset;
            float pH1 = targetProfile.points[i].pH;
            float pH2 = targetProfile.points[i+1].pH;
            
            float ratio = (currentHours - t1) / (t2 - t1);
            return pH1 + ratio * (pH2 - pH1);
        }
    }
    
    // Beyond profile end - use last value
    return targetProfile.points[targetProfile.numPoints - 1].pH;
}
```

---

## BLE Communication with Tilt Pi

### Why BLE Instead of WiFi?

✅ **Lower power** - Important for battery backup
✅ **Simpler pairing** - No network configuration
✅ **Better security** - Encrypted at protocol level
✅ **Local only** - No internet dependency
✅ **Standard protocol** - Same as Tilt Hydrometer

### BLE Service Structure

```cpp
// UUIDs (generate unique ones for pHloat Pro)
#define SERVICE_UUID           "12345678-1234-1234-1234-123456789abc"
#define CHARACTERISTIC_PH_UUID "12345678-1234-1234-1234-123456789abd"
#define CHARACTERISTIC_TEMP_UUID "12345678-1234-1234-1234-123456789abe"
#define CHARACTERISTIC_DOSE_UUID "12345678-1234-1234-1234-123456789abf"
#define CHARACTERISTIC_STATUS_UUID "12345678-1234-1234-1234-123456789ac0"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLEServer* pServer = NULL;
BLECharacteristic* pPHCharacteristic = NULL;
BLECharacteristic* pTempCharacteristic = NULL;
BLECharacteristic* pDoseCharacteristic = NULL;
BLECharacteristic* pStatusCharacteristic = NULL;

bool deviceConnected = false;

class ServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("BLE device connected");
    }

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("BLE device disconnected");
        // Restart advertising
        pServer->startAdvertising();
    }
};

void setupBLE() {
    // Create device
    BLEDevice::init("pHloat-Pro-001");  // Unique name per device
    
    // Create server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    
    // Create service
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    // Create characteristics
    pPHCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_PH_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pPHCharacteristic->addDescriptor(new BLE2902());
    
    pTempCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_TEMP_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pTempCharacteristic->addDescriptor(new BLE2902());
    
    pDoseCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_DOSE_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pDoseCharacteristic->addDescriptor(new BLE2902());
    
    pStatusCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_STATUS_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE
    );
    
    // Start service
    pService->start();
    
    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
    
    Serial.println("BLE advertising started");
}

void updateBLEData() {
    if (!deviceConnected) return;
    
    // Update pH
    char phStr[16];
    sprintf(phStr, "%.2f", currentPH);
    pPHCharacteristic->setValue(phStr);
    pPHCharacteristic->notify();
    
    // Update temperature
    char tempStr[16];
    sprintf(tempStr, "%.1f", currentTemp);
    pTempCharacteristic->setValue(tempStr);
    pTempCharacteristic->notify();
    
    // Update dosing info
    char doseStr[64];
    sprintf(doseStr, "A:%.1f,B:%.1f", totalAcidDosed, totalBaseDosed);
    pDoseCharacteristic->setValue(doseStr);
    pDoseCharacteristic->notify();
}
```

---

## Tilt Pi Integration Script

```python
#!/usr/bin/env python3
"""
pHloat Pro BLE Scanner for Tilt Pi

Scans for pHloat Pro devices via BLE
Combines pH data with Tilt SG data
Uploads combined data to Google Sheets
"""

from bluepy import btle
import time
import sqlite3
import json

# pHloat Pro UUIDs
PHLOAT_SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
PH_CHAR_UUID = "12345678-1234-1234-1234-123456789abd"
TEMP_CHAR_UUID = "12345678-1234-1234-1234-123456789abe"
DOSE_CHAR_UUID = "12345678-1234-1234-1234-123456789abf"

class PHloatScanner(btle.Scanner):
    def __init__(self):
        btle.Scanner.__init__(self)
        self.phloat_devices = {}
    
    def handleDiscovery(self, dev, isNewDev, isNewData):
        if PHLOAT_SERVICE_UUID in dev.getScanData():
            # Found pHloat Pro device
            device_name = dev.getValueText(9) or "Unknown"
            
            if device_name.startswith("pHloat-Pro"):
                print(f"Found pHloat Pro: {device_name} at {dev.addr}")
                self.phloat_devices[dev.addr] = {
                    'name': device_name,
                    'device': dev
                }

def read_phloat_data(address):
    """Connect to pHloat Pro and read data"""
    try:
        peripheral = btle.Peripheral(address)
        
        # Get service
        service = peripheral.getServiceByUUID(PHLOAT_SERVICE_UUID)
        
        # Read characteristics
        ph_char = service.getCharacteristics(PH_CHAR_UUID)[0]
        temp_char = service.getCharacteristics(TEMP_CHAR_UUID)[0]
        dose_char = service.getCharacteristics(DOSE_CHAR_UUID)[0]
        
        ph_value = float(ph_char.read().decode())
        temp_value = float(temp_char.read().decode())
        dose_value = dose_char.read().decode()
        
        peripheral.disconnect()
        
        return {
            'pH': ph_value,
            'temperature': temp_value,
            'dosing': dose_value
        }
    except Exception as e:
        print(f"Error reading pHloat Pro: {e}")
        return None

def main():
    print("pHloat Pro BLE Scanner starting...")
    
    scanner = PHloatScanner()
    
    while True:
        # Scan for devices
        scanner.scan(5.0)
        
        # Read data from each device
        for addr, info in scanner.phloat_devices.items():
            data = read_phloat_data(addr)
            if data:
                print(f"{info['name']}: pH {data['pH']:.2f}, "
                      f"Temp {data['temperature']:.1f}°C, "
                      f"Dosing: {data['dosing']}")
                
                # Store in database (integrate with existing Tilt Pi DB)
                # ... (similar to existing pHloat Tilt Pi integration)
        
        time.sleep(60)  # Scan every minute

if __name__ == '__main__':
    main()
```

---

## Safety Features

### Critical Safety Systems

```cpp
// Safety limits
#define MAX_DOSE_PER_HOUR 500.0     // ml total
#define MAX_CONSECUTIVE_DOSES 10     // Stop if stuck
#define MAX_PH_DEVIATION 1.0         // Alert if pH changes > 1.0
#define MIN_TIME_BETWEEN_DOSES 300   // seconds (5 min)
#define RESERVOIR_MIN_LEVEL 100      // ml (low level alert)

// Safety state
unsigned long lastDoseTime = 0;
int consecutiveDoses = 0;
float totalDosedThisHour = 0;
unsigned long hourStartTime = 0;

bool safetyCheck(float doseVolume) {
    unsigned long now = millis();
    
    // Check time between doses
    if ((now - lastDoseTime) < (MIN_TIME_BETWEEN_DOSES * 1000)) {
        Serial.println("SAFETY: Too soon since last dose");
        return false;
    }
    
    // Check hourly limit
    if (now - hourStartTime > 3600000) {
        // New hour
        totalDosedThisHour = 0;
        hourStartTime = now;
        consecutiveDoses = 0;
    }
    
    if (totalDosedThisHour + doseVolume > MAX_DOSE_PER_HOUR) {
        Serial.println("SAFETY: Hourly dose limit exceeded!");
        sendAlert("Hourly dose limit reached");
        return false;
    }
    
    // Check consecutive doses
    if (consecutiveDoses >= MAX_CONSECUTIVE_DOSES) {
        Serial.println("SAFETY: Too many consecutive doses!");
        sendAlert("System may be stuck - check equipment");
        return false;
    }
    
    // Check pH deviation
    if (abs(currentPH - previousPH) > MAX_PH_DEVIATION) {
        Serial.println("SAFETY: Extreme pH change detected!");
        sendAlert("Abnormal pH change - check probe");
        return false;
    }
    
    // Check reservoir levels
    if (acidReservoirLevel < RESERVOIR_MIN_LEVEL) {
        Serial.println("WARNING: Acid reservoir low");
        sendAlert("Refill acid reservoir");
    }
    if (baseReservoirLevel < RESERVOIR_MIN_LEVEL) {
        Serial.println("WARNING: Base reservoir low");
        sendAlert("Refill base reservoir");
    }
    
    return true;
}
```

### Fail-Safe Modes

```cpp
enum SystemMode {
    MODE_MONITOR_ONLY,    // No dosing, just monitor
    MODE_MANUAL,          // Manual dosing only
    MODE_AUTO_CAUTIOUS,   // Conservative PID
    MODE_AUTO_NORMAL,     // Normal PID
    MODE_EMERGENCY_STOP   // All dosing disabled
};

SystemMode currentMode = MODE_MONITOR_ONLY;

void checkFailSafes() {
    // Probe failure detection
    if (currentPH < 0 || currentPH > 14) {
        Serial.println("FAIL-SAFE: Invalid pH reading!");
        currentMode = MODE_EMERGENCY_STOP;
        stopAllPumps();
        return;
    }
    
    // Communication loss
    if (millis() - lastBLEUpdate > 300000) {  // 5 minutes
        Serial.println("FAIL-SAFE: Lost communication!");
        currentMode = MODE_EMERGENCY_STOP;
        stopAllPumps();
        return;
    }
    
    // Pump failure (check with flow sensors if equipped)
    if (pumpCommandedOn && flowRate < 0.1) {
        Serial.println("FAIL-SAFE: Pump not flowing!");
        currentMode = MODE_EMERGENCY_STOP;
        stopAllPumps();
        return;
    }
}
```

---

## Complete Main Code Structure

```cpp
/*
 * pHloat Pro - Professional pH Control System
 * 
 * Features:
 * - BLE communication with Tilt Pi
 * - PID-based pH control
 * - Dual peristaltic pump dosing
 * - Fermentation profile learning/replay
 * - Comprehensive safety systems
 * 
 * Hardware:
 * - ESP32-S3
 * - Atlas Scientific pH OEM
 * - 2× Peristaltic pumps
 * - L298N motor driver
 */

#include <BLEDevice.h>
#include <Wire.h>
#include <SPIFFS.h>

// Pin definitions
#define I2C_SDA 8
#define I2C_SCL 9
#define PUMP_ACID_PIN 4
#define PUMP_BASE_PIN 5
#define PH_SENSOR_ADDR 0x63

// Global objects
PHController pidController;
FermentationProfile currentProfile;

// State variables
float currentPH = 7.0;
float currentTemp = 20.0;
float currentSG = 1.050;
unsigned long pitchTime = 0;
bool autoMode = false;

void setup() {
    Serial.begin(115200);
    Serial.println("pHloat Pro starting...");
    
    // Initialize I2C
    Wire.begin(I2C_SDA, I2C_SCL);
    
    // Initialize GPIO
    pinMode(PUMP_ACID_PIN, OUTPUT);
    pinMode(PUMP_BASE_PIN, OUTPUT);
    digitalWrite(PUMP_ACID_PIN, LOW);
    digitalWrite(PUMP_BASE_PIN, LOW);
    
    // Initialize SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS mount failed");
    }
    
    // Initialize BLE
    setupBLE();
    
    // Set initial PID parameters
    pidController.setGains(2.0, 0.5, 1.0);
    pidController.setTarget(4.5, 0.05, 0.05);
    
    Serial.println("pHloat Pro ready!");
}

void loop() {
    // Read pH
    currentPH = readPH();
    currentTemp = readTemperature();
    
    // Get SG from Tilt (via BLE - implement separately)
    // currentSG = getTiltSG();
    
    // Update BLE
    updateBLEData();
    
    // Check safety systems
    checkFailSafes();
    
    // Auto control if enabled
    if (autoMode && currentMode == MODE_AUTO_NORMAL) {
        performDosing(currentPH);
    }
    
    // Profile tracking
    if (replayMode) {
        followProfile();
    }
    
    // Log data
    logData();
    
    // Wait before next reading
    delay(60000);  // 1 minute
}

float readPH() {
    Wire.beginTransmission(PH_SENSOR_ADDR);
    Wire.write('R');
    Wire.endTransmission();
    
    delay(900);
    
    Wire.requestFrom(PH_SENSOR_ADDR, 20);
    byte code = Wire.read();
    
    if (code != 1) {
        Serial.println("pH read error");
        return -1;
    }
    
    char data[20];
    int i = 0;
    while (Wire.available() && i < 19) {
        data[i++] = Wire.read();
    }
    data[i] = '\0';
    
    return atof(data);
}
```

---

## Next Steps Document

See **PHLOAT_PRO_BUILD_GUIDE.md** (to be created) for:
- Detailed assembly instructions
- Tri-clamp installation
- Pump calibration procedures
- PID tuning walkthrough
- Profile creation examples
- Safety testing procedures
- Troubleshooting guide

---

**This is a professional system - test thoroughly before deploying to valuable fermentations!**
