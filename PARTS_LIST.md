# pHloat Parts Shopping List

## For One Complete System (1 Relay + 1 Sensor)

### pH Sensor Assembly

| Item | Specifications | Qty | Est. Cost | Where to Buy | Notes |
|------|----------------|-----|-----------|--------------|-------|
| **ESP32-S3 Development Board** | With battery charging circuit, USB-C preferred | 1 | $10-15 | Amazon, AliExpress | Look for "ESP32-S3 with battery management" |
| **Atlas Scientific pH OEM Circuit** | I2C mode, 3.3V operation | 1 | $60 | atlas-scientific.com | Part #: ENV-SDS-PH |
| **pH Probe with BNC** | Standard lab-grade probe | 1 | $50-100 | Atlas Scientific or Amazon | Atlas PT-1000 or equivalent |
| **LiPo Battery** | 3.7V, 2000-3000mAh, JST connector | 1 | $10 | Amazon, Battery suppliers | Ensure JST matches your ESP32 |
| **Waterproof Enclosure** | IP67, ~100x60x40mm | 1 | $12 | Amazon | Must fit ESP32 + Atlas circuit |
| **BNC Panel Mount Connector** | Female BNC | 1 | $5 | Amazon, Digikey | For probe to pass through enclosure |
| **Jumper Wires** | Female-female, 10cm | 4 | $2 | Amazon | For I2C connections |
| **Silicone Sealant** | Waterproof, food-safe | 1 | $6 | Hardware store | To seal enclosure openings |

**Sensor Subtotal: ~$155-200 per sensor**

### Relay Assembly

| Item | Specifications | Qty | Est. Cost | Where to Buy | Notes |
|------|----------------|-----|-----------|--------------|-------|
| **ESP32 Development Board** | Any ESP32 variant | 1 | $8 | Amazon, AliExpress | ESP32-DevKitC or similar |
| **USB Power Supply** | 5V, 1A minimum | 1 | $6 | Amazon | Phone charger works |
| **Micro USB Cable** | Or USB-C depending on board | 1 | $3 | Amazon | - |
| **Enclosure (optional)** | Small project box | 1 | $8 | Amazon | Optional but recommended |

**Relay Subtotal: ~$25**

### Calibration & Maintenance Supplies

| Item | Specifications | Qty | Est. Cost | Where to Buy | Notes |
|------|----------------|-----|-----------|--------------|-------|
| **pH 4.0 Buffer Solution** | 500ml | 1 | $8 | Amazon, lab suppliers | For calibration |
| **pH 7.0 Buffer Solution** | 500ml | 1 | $8 | Amazon, lab suppliers | For calibration |
| **pH 10.0 Buffer Solution** | 500ml | 1 | $8 | Amazon, lab suppliers | For calibration |
| **pH Probe Storage Solution** | 500ml | 1 | $10 | Amazon, Atlas Scientific | Critical for probe life |
| **pH Probe Cleaning Solution** | 100ml | 1 | $12 | Amazon, Atlas Scientific | Monthly cleaning |
| **Distilled Water** | 1 gallon | 1 | $3 | Grocery store | For rinsing probe |

**Calibration Supplies Subtotal: ~$50** (one-time purchase, lasts for years)

## Total System Cost

| Component | Cost |
|-----------|------|
| 1x pH Sensor | $155-200 |
| 1x Relay | $25 |
| Calibration supplies | $50 |
| **TOTAL for 1-sensor system** | **$230-275** |

### Additional Sensors
Each additional sensor: $155-200 (no need for additional relay or calibration supplies)

## Recommended Suppliers

### Electronics
- **Amazon** - Fast shipping, good for batteries, enclosures, general electronics
- **AliExpress** - Cheapest ESP32 boards (longer shipping)
- **Adafruit** - Quality components, good support
- **SparkFun** - Quality components, tutorials
- **Digi-Key** - Professional grade, fast shipping

### pH Equipment
- **Atlas Scientific** (atlas-scientific.com)
  - Official source for pH OEM circuits
  - High-quality probes
  - Calibration and storage solutions
  - Excellent technical support
- **Amazon**
  - Third-party pH probes (cheaper but variable quality)
  - Calibration buffers
  - Storage solutions
- **Local laboratory suppliers**
  - Often have buffer solutions in stock
  - Can provide advice on probe care

## Specific Product Recommendations

### ESP32-S3 Board
**Recommended:** "ESP32-S3 DevKitC with Battery Management"
- Look for boards with:
  - Built-in LiPo charging circuit
  - USB-C connector
  - At least 4MB flash
  - Clear GPIO pinout labels
  
**Example search terms:**
- "ESP32-S3 battery charging"
- "ESP32-S3 DevKit LiPo"
- "LILYGO T-Display-S3" (has display, optional)

### pH Probe
**Budget Option (~$50):**
- Generic "BNC pH Electrode" from Amazon
- Look for gel-filled probes
- Temperature range: 0-80°C minimum

**Quality Option (~$100):**
- Atlas Scientific PT-1000 Consumer Grade pH Probe
- Higher accuracy and longer life
- Better temperature compensation

**Professional Option (~$200+):**
- Atlas Scientific PT-1000 Lab Grade pH Probe
- Laboratory accuracy
- Refillable electrolyte
- Longest lifespan

### LiPo Battery
**Recommended specs:**
- Capacity: 2000-3000mAh
- Voltage: 3.7V (nominal)
- Protection circuit: Built-in (important!)
- Connector: JST-PH 2.0mm (most common for ESP32)

**Example search:** "3.7V 2500mAh LiPo JST"

### Enclosure
**Requirements:**
- Size: ~100x60x40mm (4"x2.4"x1.6") minimum
- Rating: IP67 or better
- Material: ABS plastic
- Features: Mounting holes, cable gland for probe

**Example search:** "IP67 ABS project box 100x60mm"

## Money-Saving Tips

1. **Buy in bulk:**
   - If building multiple sensors, buy ESP32s from AliExpress (5-pack deals)
   - Calibration supplies last for many sensors
   
2. **Generic vs branded:**
   - Atlas Scientific pH OEM is worth the cost (very reliable)
   - pH probe can be generic for hobbyist use
   - ESP32 boards are all similar (go cheap)
   
3. **Reuse what you have:**
   - Old phone chargers for relay power
   - Any USB cable works
   - Project boxes from other projects
   
4. **Wait for sales:**
   - Amazon Prime Day often has deals on electronics
   - AliExpress has regular sales
   
5. **Share supplies:**
   - Split calibration buffers with brewing friends
   - Buy ESP32s in bulk and split

## What NOT to Cheap Out On

1. **pH Probe Storage Solution** - Critical for probe life, don't skip this
2. **Waterproof Enclosure** - Water damage will kill your sensor
3. **Quality Battery** - Cheap batteries can be dangerous
4. **Atlas pH OEM Circuit** - Third-party pH circuits are unreliable

## Optional Upgrades

| Item | Purpose | Cost | Worth It? |
|------|---------|------|-----------|
| Temperature probe for Atlas circuit | Better temp compensation | $30 | Yes if brewing lagers |
| Solar panel + charge controller | Never change battery | $25 | Maybe for outdoor use |
| Larger battery (5000mAh) | 6+ months runtime | $15 | Yes if you hate charging |
| Second relay (backup) | Redundancy | $25 | No, just reflash if it dies |
| Professional pH probe | ±0.01 pH accuracy | $200+ | Only for very serious brewers |

## Kit Assembly Suggestion

If you're planning to outfit an entire brewery:

**Small Brewery Kit (3 fermenters):**
- 1x Relay: $25
- 3x pH Sensors: $165 each = $495
- 1x Calibration set: $50
- **Total: $570** (~$190 per fermenter)

**Medium Brewery Kit (6 fermenters):**
- 1x Relay: $25
- 6x pH Sensors: $165 each = $990
- 1x Calibration set: $50
- **Total: $1,065** (~$178 per fermenter)

**Large Brewery Kit (10 fermenters):**
- 2x Relays: $50 (one per 6 sensors, or backup)
- 10x pH Sensors: $165 each = $1,650
- 1x Calibration set: $50
- **Total: $1,750** (~$175 per fermenter)

## Checklist Before Ordering

- [ ] Verified ESP32-S3 has battery charging circuit
- [ ] Checked battery connector matches ESP32 board (usually JST)
- [ ] Enclosure large enough for ESP32 + Atlas circuit
- [ ] BNC connector fits enclosure
- [ ] Have USB cable for programming
- [ ] Ordered all three pH buffers (4, 7, 10)
- [ ] Ordered storage solution (critical!)
- [ ] Have jumper wires for I2C connections
- [ ] Have silicone sealant for waterproofing

## Return Policy Note

Test everything before installing in enclosures or fermenters:
- Test ESP32 boards immediately upon receipt
- Test pH circuits with probes BEFORE calibration
- Keep packaging for 30 days in case of returns
- Document any issues with photos/video

## Warranty Information

- **Atlas Scientific:** 1-year warranty on circuits, check probe warranty
- **ESP32 boards:** Usually 30-day seller warranty
- **Batteries:** Typically no warranty (consumable item)
- **Enclosures:** Usually no warranty needed

---

**Total Time to Acquire All Parts:** 1-2 weeks (depending on suppliers)
**Total Assembly Time:** 2-3 hours per sensor (first time), 30 min (after practice)
