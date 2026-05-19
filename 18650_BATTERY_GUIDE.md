# Using 18650 Batteries with pHloat System

## Overview

This guide explains how to modify the pHloat system to use **18650 lithium-ion cells** instead of LiPo pouches. 18650s are an excellent choice for this application!

## Why 18650 Batteries?

### Advantages over LiPo Pouches

✅ **More durable** - Hard shell protects cells from damage
✅ **Safer** - Less prone to puncture/swelling
✅ **Easier to source** - Available everywhere (laptop batteries, vape shops, etc.)
✅ **Standard size** - 18mm diameter × 65mm length
✅ **Often cheaper** - Especially if you reclaim from old laptop batteries
✅ **Higher capacity options** - Up to 3500mAh per cell
✅ **Better for cold environments** - More stable in temperature swings
✅ **Replaceable** - Easy to swap without soldering

### Considerations

⚠️ **Slightly larger** - Need bigger enclosure (but not much)
⚠️ **Heavier** - ~45g vs ~25g for LiPo pouch
⚠️ **Need proper holder** - Can't just tape them like LiPo pouches
⚠️ **Protection circuit critical** - MUST use protected cells or protection board

## Battery Specifications

### Recommended 18650 Cells

**For pHloat Sensors (Best to Worst):**

1. **Samsung INR18650-35E** (3500mAh, $5-8)
   - Highest capacity
   - Excellent for long runtime
   - 8A continuous discharge (more than enough)
   - Battery life: ~130 days per charge

2. **Panasonic NCR18650B** (3400mAh, $5-7)
   - Very popular, widely available
   - Reliable and safe
   - Battery life: ~125 days per charge

3. **LG INR18650-MJ1** (3500mAh, $6-8)
   - Similar to Samsung 35E
   - Good availability
   - Battery life: ~130 days per charge

4. **Protected Generic 18650** (2200-3000mAh, $3-5)
   - Budget option
   - Battery life: 80-110 days per charge
   - **IMPORTANT:** Must be "protected" cells with built-in PCB

### CRITICAL: Use Protected Cells

**ALWAYS use protected 18650 cells** or add a protection circuit board. Protection prevents:
- Over-discharge (< 2.5V)
- Over-charge (> 4.2V)
- Short circuits
- Over-current

**Identifying protected cells:**
- Slightly longer than 65mm (usually 67-69mm)
- Has small PCB visible at negative terminal
- Product description says "protected"
- Usually costs $1-2 more than unprotected

**DON'T use unprotected cells** unless you add a separate protection board!

## Hardware Changes

### For pH Sensors

#### Option 1: Single 18650 (Simplest)

**What you need:**
- 1× Protected 18650 cell (3.7V, 2500-3500mAh)
- 1× 18650 single-cell holder with leads
- 1× TP4056 charging module with protection (if cell isn't protected)
- ESP32-S3 board with built-in battery management

**Wiring:**
```
18650 Cell in Holder
    │
    ├─ Positive (+) ──→ TP4056 B+ (battery positive)
    ├─ Negative (-) ──→ TP4056 B- (battery negative)
    
TP4056 Module
    │
    ├─ OUT+ ──→ ESP32-S3 Battery Positive (JST connector)
    ├─ OUT- ──→ ESP32-S3 Battery Negative (JST connector)
    ├─ IN+  ──→ USB 5V (for charging)
    └─ IN-  ──→ USB GND (for charging)
```

**Battery Life Calculation:**
- 3500mAh 18650 @ 80% usable capacity = 2800mAh effective
- Current draw: ~0.8mA average
- Runtime: 2800mAh ÷ 21.6mAh/day = **130 days per charge**

**Pros:**
- Simplest modification
- Same voltage as LiPo (3.7V nominal)
- Direct replacement
- Easy to charge

**Cons:**
- Slightly less capacity than 2× 18650
- Need external charger or TP4056 module

#### Option 2: Two 18650s in Parallel (Maximum Runtime)

**What you need:**
- 2× Protected 18650 cells (matched pair)
- 1× 18650 dual-cell holder (parallel configuration)
- 1× TP4056 module (optional, for USB charging)
- ESP32-S3 board with battery management

**Wiring:**
```
Two 18650s in PARALLEL (both 3.7V → combined still 3.7V)
    │
    ├─ Positive (+) ──→ ESP32-S3 Battery +
    └─ Negative (-) ──→ ESP32-S3 Battery -

Capacity: 3500mAh × 2 = 7000mAh
Battery life: ~260 days per charge!
```

**IMPORTANT:** 
- Cells must be matched (same brand, capacity, age)
- Cells must be balanced (same voltage when installed)
- Use protected cells to prevent issues

**Pros:**
- Incredible battery life (8+ months!)
- Higher capacity = more stable voltage
- Less frequent charging

**Cons:**
- Larger enclosure needed
- Heavier
- More expensive (2 cells)
- Must balance cells

### For pH Relay (if battery-powered)

**Note:** The relay is typically wall-powered, but if you want it battery-powered:

#### Power Requirements
- Relay draws ~150mA continuous (WiFi on)
- Much higher than sensor
- Need larger capacity

#### Recommended Setup: 4× 18650 in 2S2P

**What you need:**
- 4× Protected 18650 cells (matched set)
- 1× 4-cell holder (2S2P configuration: 2 series, 2 parallel)
- 1× 2S BMS (Battery Management System) board
- 1× DC-DC buck converter (7.4V → 5V)

**Configuration:**
```
2S2P = Two Series, Two Parallel
- 2 cells in series = 7.4V
- 2 cells in parallel with above = 7.4V at double capacity

Voltage: 3.7V × 2 = 7.4V
Capacity: 3500mAh × 2 = 7000mAh

Runtime: 7000mAh ÷ 150mA = 46 hours (2 days)
```

**Better option:** Just use wall power for relay! 
- Relay needs continuous power
- Battery-powered relay not practical
- Save the 18650s for sensors

## Component Shopping List

### For Single 18650 Sensor (Recommended)

| Item | Specification | Qty | Cost | Where |
|------|--------------|-----|------|-------|
| **18650 Protected Cell** | 3500mAh, protected | 1 | $5-8 | Amazon, battery stores |
| **18650 Single Holder** | With wire leads | 1 | $1-2 | Amazon, eBay |
| **TP4056 Charging Module** | With protection, micro-USB | 1 | $1-2 | Amazon, AliExpress |
| **JST Connector** (optional) | To match ESP32 | 1 | $1 | Amazon |
| **Larger Enclosure** | ~110×65×45mm | 1 | $12-15 | Amazon |

**Total added cost vs LiPo:** ~$0-5 (18650s often cheaper!)

### Recommended Products

**18650 Cells:**
- Search: "protected 18650 3500mah"
- Brands: Samsung, Panasonic, LG, Sony
- Avoid: UltraFire, "9900mAh" claims (fake)
- Price: $5-8 per cell

**18650 Holders:**
- Search: "18650 single holder with leads"
- Choose: Spring-loaded, wire leads
- Avoid: PCB-mount holders (harder to use)
- Price: $1-2

**TP4056 Modules:**
- Search: "TP4056 battery charging module protection"
- Features: Micro-USB, LED indicators, protection
- Get the version WITH protection circuit
- Price: $1-2 for 5-pack

**18650 Chargers (External):**
- Search: "18650 charger 4-bay"
- Brands: XTAR, Nitecore, Efest
- Get one with individual cell monitoring
- Price: $15-30 (charges 4 cells at once)

## Enclosure Modifications

### Size Requirements

**LiPo (original):**
- ~50×30×8mm

**Single 18650:**
- 18mm diameter × 65-69mm length
- Holder adds ~5mm to each dimension

**Enclosure recommendations:**

| Sensors | Original Size | With 18650 | Recommended |
|---------|--------------|------------|-------------|
| 1× 18650 | 100×60×40mm | 110×65×45mm | Just slightly larger |
| 2× 18650 (parallel) | 100×60×40mm | 120×70×50mm | Moderately larger |

**Good enclosures:**
- Hammond 1591XXCSBK (110×60×40mm) - Perfect for 1× 18650
- Fibox TEMPO TAM121207 (120×120×75mm) - Good for 2× 18650

## Wiring Diagrams

### Single 18650 with TP4056 Charging Module

```
╔═══════════════════════════════════════════════════════════════╗
║              Single 18650 Configuration (RECOMMENDED)         ║
╚═══════════════════════════════════════════════════════════════╝

                    ┌─────────────────┐
                    │  18650 Cell     │
                    │  (Protected)    │
                    │  3.7V 3500mAh   │
                    └────┬──────┬─────┘
                         │      │
                    (+)  │      │  (-)
                         │      │
                    ┌────▼──────▼─────┐
                    │  18650 Holder   │
                    │  with Leads     │
                    └────┬──────┬─────┘
                         │      │
                    Red  │      │  Black
                         │      │
            ┌────────────▼──────▼─────────────┐
            │     TP4056 Charging Module      │
            │                                 │
            │  B+  B-          OUT+  OUT-     │
            │   ↑   ↑            ↑    ↑       │
            └───┼───┼────────────┼────┼───────┘
                │   │            │    │
                │   │    ┌───────┘    │
                │   │    │    ┌───────┘
                │   │    │    │
            ┌───▼───▼────▼────▼───────────┐
            │      ESP32-S3                │
            │                              │
            │  BAT+ GND                    │
            │                              │
            │  GPIO 8 (SDA) ──────┐        │
            │  GPIO 9 (SCL) ──────┼────┐   │
            │  3.3V        ────────┼────┼─┐ │
            │  GND         ────────┼────┼─┼─┤
            └──────────────────────┼────┼─┼─┘
                                   │    │ │ │
                          ┌────────▼────▼─▼─▼─────┐
                          │  Atlas Scientific     │
                          │  pH OEM Circuit       │
                          │                       │
                          │  SDA SCL VCC GND      │
                          └───────────────────────┘

USB Charging:
    USB Cable → TP4056 IN+ / IN-
    TP4056 charges 18650
    Red LED = Charging
    Blue LED = Charged
```

### Dual 18650 (Parallel) - Maximum Runtime

```
╔═══════════════════════════════════════════════════════════════╗
║         Dual 18650 Parallel (For Maximum Runtime)            ║
╚═══════════════════════════════════════════════════════════════╝

    ┌───────────────┐      ┌───────────────┐
    │  18650 Cell 1 │      │  18650 Cell 2 │
    │  3.7V 3500mAh │      │  3.7V 3500mAh │
    └───┬────┬──────┘      └───┬────┬──────┘
        │    │                 │    │
       (+)  (-)               (+)  (-)
        │    │                 │    │
    ┌───▼────▼─────────────────▼────▼───┐
    │   2-Cell 18650 Holder             │
    │   (Parallel Configuration)        │
    │                                   │
    │   Combined: 3.7V @ 7000mAh        │
    └───┬────────────────────────┬──────┘
        │                        │
    Red │                        │ Black
        │                        │
    ┌───▼────────────────────────▼──────┐
    │        ESP32-S3 Battery IN        │
    │                                   │
    │    (No TP4056 needed - direct)   │
    └───────────────────────────────────┘

IMPORTANT: 
- Cells MUST be matched (same brand, model, age)
- Cells MUST be balanced (same voltage)
- Use protected cells ONLY
- Runtime: ~260 days!
```

## Assembly Instructions

### Step 1: Prepare 18650 Cell

1. **Check cell voltage:**
   ```
   Use multimeter
   Should read: 3.6-4.2V
   If below 3.0V: Cell may be damaged
   ```

2. **Inspect cell:**
   - No dents or damage
   - Wrapper intact (no exposed metal)
   - Clean terminals
   - If protected: Can see small PCB at negative end

3. **Test capacity (optional but recommended):**
   - Use 18650 charger with capacity test
   - Should read close to rated capacity
   - If much lower: Cell is worn out

### Step 2: Install in Holder

1. **Check polarity:**
   - Flat end (negative) has spring or label
   - Button end (positive) opposite side
   - Holder is marked with + / -

2. **Insert cell:**
   - Negative end first (into spring)
   - Press positive end down
   - Should click and be secure

3. **Verify polarity with multimeter:**
   - Red lead on red wire → should be ~3.7V
   - Black lead on black wire
   - If negative voltage: Wires are reversed!

### Step 3: Wire to TP4056 Module

1. **TP4056 connections:**
   ```
   18650 Holder    →    TP4056
   ────────────────────────────
   Red wire (+)    →    B+
   Black wire (-)  →    B-
   ```

2. **Solder or use screw terminals:**
   - If soldering: Tin wires first
   - Use heat shrink to insulate
   - Double-check polarity!

3. **Add JST connector (optional):**
   ```
   TP4056          →    JST Connector    →    ESP32
   ────────────────────────────────────────────────
   OUT+            →    Red wire        →    BAT+
   OUT-            →    Black wire      →    GND
   ```

### Step 4: Test Charging

1. **Connect USB cable to TP4056:**
   - Red LED should light (charging)
   - Check 18650 voltage: Should be rising

2. **Wait for full charge:**
   - Red LED turns off or blue LED turns on
   - Cell voltage: 4.15-4.20V
   - Takes 2-5 hours for full charge

3. **Disconnect USB:**
   - Voltage should stay at 4.1-4.2V
   - If drops quickly: Cell or module problem

### Step 5: Connect to ESP32

1. **Power off everything first!**

2. **Connect to ESP32-S3:**
   - TP4056 OUT+ → ESP32 BAT+
   - TP4056 OUT- → ESP32 GND
   - If using JST: Plug into battery connector

3. **Test power:**
   - ESP32 should power on
   - Check battery voltage in serial monitor
   - Should read 3.7-4.2V

### Step 6: Mount in Enclosure

1. **Secure 18650 holder:**
   - Hot glue, velcro, or screws
   - Keep away from circuit boards
   - Allow air circulation

2. **Secure TP4056 module:**
   - Mount near USB port hole
   - Keep accessible for charging LED visibility

3. **Wire routing:**
   - Keep battery wires away from I2C lines
   - Use zip ties or cable management
   - Strain relief at all connections

## Charging Options

### Option 1: USB Charging (with TP4056)

**Pros:**
- ✅ Charge without removing battery
- ✅ Charge indicator LEDs
- ✅ Can charge while deployed
- ✅ Built-in protection

**Cons:**
- ❌ Slightly larger circuit
- ❌ Adds $1-2 to cost

**Setup:**
- Drill hole in enclosure for micro-USB port
- Mount TP4056 near hole
- Add rubber grommet for waterproofing
- Charge with any micro-USB cable

### Option 2: External Charger (Remove Battery)

**Pros:**
- ✅ Simpler electronics (no TP4056)
- ✅ Faster charging (1-2A vs 500mA)
- ✅ Can balance multiple cells
- ✅ Cell capacity testing available

**Cons:**
- ❌ Must open enclosure
- ❌ Must remove battery
- ❌ Need separate charger ($15-30)

**Recommended chargers:**
- Nitecore D4 (~$25) - 4 bay, 1A per slot
- XTAR VC4 (~$30) - 4 bay, LCD display
- Efest LUC V4 (~$25) - 4 bay, simple

### Option 3: Hybrid (Best of Both)

**Setup:**
- Install TP4056 for convenience charging
- Keep external charger for fast charging
- Use TP4056 for field charges
- Use external charger at home for fast charge

**Why this is best:**
- Convenience when deployed
- Fast charging when home
- Can test cell capacity with external charger

## Battery Life Comparison

### LiPo vs 18650 Runtime

| Battery | Capacity | Usable | Runtime (days) |
|---------|----------|--------|----------------|
| **LiPo 2000mAh** | 2000mAh | 1600mAh | ~74 days |
| **18650 2500mAh** | 2500mAh | 2000mAh | ~93 days |
| **18650 3000mAh** | 3000mAh | 2400mAh | ~111 days |
| **18650 3500mAh** | 3500mAh | 2800mAh | ~130 days |
| **2× 18650 3500mAh** | 7000mAh | 5600mAh | ~260 days |

*Assumes 0.8mA average draw, 80% usable capacity*

### Real-World Runtime

**Factors that reduce runtime:**
- Cold temperatures (can reduce by 20-30%)
- Aged cells (capacity decreases over time)
- WiFi strength (weak signal = more power)
- Number of transmission retries

**Factors that increase runtime:**
- Warm temperatures (optimal: 20-25°C)
- New cells at peak capacity
- Strong WiFi signal
- Successful first transmission

## Safety Considerations

### 18650 Safety Rules

⚠️ **CRITICAL SAFETY RULES:**

1. **NEVER use damaged cells**
   - No dents, tears in wrapper
   - No exposed metal
   - No signs of leaking

2. **ALWAYS use protected cells** (or protection board)
   - Prevents over-discharge
   - Prevents over-charge
   - Prevents short circuit

3. **NEVER mix different cells**
   - Same brand, model, capacity
   - Same age / charge cycles
   - Especially critical for parallel config

4. **NEVER short circuit**
   - Keep away from metal objects
   - Insulate all connections
   - Use proper holders

5. **Monitor temperature**
   - Should stay cool during charge
   - If hot: Disconnect immediately
   - Normal: Slightly warm is OK

6. **Proper storage**
   - Store at 40-60% charge (3.7-3.8V)
   - Cool, dry location
   - In non-conductive case
   - Never in hot car

### Warning Signs

🚨 **Stop using immediately if:**
- Cell is hot to touch
- Sweet/chemical smell
- Hissing sound
- Wrapper damaged/torn
- Cell is swollen/bulging
- Voltage drops below 2.5V

### Disposal

♻️ **Proper disposal:**
- Don't throw in trash
- Take to battery recycling center
- Home Depot, Best Buy, battery stores accept them
- Discharge to ~3.0V before recycling
- Tape terminals to prevent shorts

## Troubleshooting

### Battery Won't Charge

**Check:**
1. TP4056 has power (USB connected)
2. Cell polarity correct (measure with multimeter)
3. Cell isn't over-discharged (< 2.0V)
4. TP4056 isn't damaged (check for burn marks)
5. Wiring connections secure

**Solutions:**
- Check all connections
- Measure TP4056 input voltage (should be 5V)
- Measure battery voltage
- Try different cell
- Replace TP4056 module ($1)

### Short Battery Life

**Check:**
1. Cell capacity (test with charger)
2. Deep sleep working (serial monitor confirms)
3. WiFi signal strength
4. Temperature (cold reduces capacity)
5. Cell age (worn cells have less capacity)

**Solutions:**
- Test cell capacity with external charger
- Verify deep sleep in code
- Move closer to relay/WiFi
- Use fresh, high-capacity cells
- Check for parasitic drain

### ESP32 Won't Power On

**Check:**
1. Battery voltage (should be > 3.3V)
2. Connections secure
3. Correct polarity
4. ESP32 not damaged

**Solutions:**
- Charge battery fully (4.1-4.2V)
- Check all solder joints
- Verify polarity with multimeter
- Try powering via USB to test ESP32

### Cells Won't Balance (Parallel Config)

**Check:**
1. Both cells same brand/model
2. Similar age and cycle count
3. Both at similar voltage when installed
4. Protection circuits working

**Solutions:**
- Use only matched cells
- Charge separately to same voltage first
- Replace if one cell is weak
- Test individual cell capacity

## Cost Comparison

### Total System Cost: LiPo vs 18650

**Single Sensor - LiPo (Original):**
| Item | Cost |
|------|------|
| ESP32-S3 + pH OEM + Probe | $170 |
| LiPo 2000mAh | $10 |
| Enclosure | $12 |
| Misc | $10 |
| **Total** | **$202** |

**Single Sensor - Single 18650:**
| Item | Cost |
|------|------|
| ESP32-S3 + pH OEM + Probe | $170 |
| 18650 3500mAh Protected | $7 |
| 18650 Holder | $1 |
| TP4056 Module | $1 |
| Enclosure (slightly larger) | $14 |
| Misc | $10 |
| **Total** | **$203** |

**Difference: +$1** (basically the same!)

**Single Sensor - Dual 18650:**
| Item | Cost |
|------|------|
| ESP32-S3 + pH OEM + Probe | $170 |
| 2× 18650 3500mAh Protected | $14 |
| 2-cell Holder | $2 |
| Enclosure (larger) | $16 |
| Misc | $10 |
| **Total** | **$212** |

**Difference: +$10** (for 260 days runtime!)

### Long-Term Cost

**Replacement cost after 2 years:**

| Battery Type | Replacement Cost |
|--------------|------------------|
| LiPo 2000mAh | $10 |
| 18650 3500mAh | $7 |
| 2× 18650 3500mAh | $14 |

**Winner: Single 18650** (cheapest long-term)

## Recommended Configuration

### For Most Users: Single 3500mAh 18650

**Why:**
- ✅ 130 day runtime (4+ months)
- ✅ Same cost as LiPo
- ✅ More durable
- ✅ Easier to source
- ✅ Simple to implement
- ✅ Small size increase

**Shopping list:**
- 1× Samsung INR18650-35E ($6)
- 1× 18650 single holder ($1)
- 1× TP4056 module ($1)
- Total: ~$8

### For Maximum Runtime: Dual 3500mAh 18650

**Why:**
- ✅ 260 day runtime (8+ months!)
- ✅ Charge twice per year
- ✅ Perfect for hard-to-reach installs
- ✅ More stable voltage

**Shopping list:**
- 2× Samsung INR18650-35E ($12)
- 1× 2-cell parallel holder ($2)
- Total: ~$14

## Code Changes Required

### Voltage Monitoring

18650 voltage range is same as LiPo, so **no code changes needed!**

```cpp
// Battery voltage monitoring (works for both LiPo and 18650)
float batteryVoltage = analogRead(BATTERY_PIN) * (3.3 / 4095.0) * 2;

// Battery percentage (same calculation)
float batteryPercent = ((batteryVoltage - 3.3) / (4.2 - 3.3)) * 100;
if (batteryPercent > 100) batteryPercent = 100;
if (batteryPercent < 0) batteryPercent = 0;
```

### Low Battery Warning

Adjust thresholds if desired:

```cpp
// For 18650 (same as LiPo)
#define BATTERY_LOW 3.4  // ~15% charge
#define BATTERY_CRITICAL 3.2  // ~5% charge

if (batteryVoltage < BATTERY_CRITICAL) {
  // Send critical battery warning
  // Reduce reading frequency
  SLEEP_DURATION = 300;  // 5 minutes instead of 1
}
```

**No changes required** - existing code works perfectly!

## Summary

### Quick Answer: Should I use 18650?

**YES, if:**
- ✅ You want longer runtime
- ✅ You want more durable batteries
- ✅ You already have 18650s
- ✅ You want cheaper long-term cost

**Stick with LiPo if:**
- ✅ You want absolute smallest size
- ✅ You already bought LiPos
- ✅ You want lightest weight

### Bottom Line

**18650s are recommended!** They're:
- Same cost or cheaper
- More durable
- Longer runtime
- Easier to find
- Safer (hard case)

The only tradeoff is ~10% larger enclosure, which is minimal.

---

**Happy brewing with longer-lasting sensors! 🍺**
