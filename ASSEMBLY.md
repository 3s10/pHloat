# pHloat Assembly Instructions

## Safety First

⚠️ **Before You Begin:**
- Work in a well-ventilated area
- Discharge static electricity before handling components
- Never solder near LiPo batteries
- Keep water away from electronics during assembly
- Wear safety glasses when drilling enclosures

## Tools Required

### Basic Tools
- Small Phillips screwdriver
- Wire strippers/cutters
- Soldering iron (optional, for permanent connections)
- Drill with 12mm bit (for BNC hole in enclosure)
- Multimeter (for testing connections)
- Hot glue gun (optional, for strain relief)

### Supplies
- Electrical tape or heat shrink tubing
- Silicone sealant (food-safe)
- Isopropyl alcohol (for cleaning)
- Label maker or permanent marker

## Part 1: pH Sensor Assembly

**Estimated Time:** 60-90 minutes (first time)

### Step 1: Prepare the Enclosure (15 min)

1. **Plan the layout:**
   ```
   Top view of enclosure:
   ┌─────────────────────────┐
   │  [ESP32]    [Atlas OEM] │
   │                         │
   │  [Battery underneath]   │
   │                         │
   │         [BNC] ←─────────┼── Drill hole here
   └─────────────────────────┘
   ```

2. **Drill BNC hole:**
   - Mark spot on side of enclosure for BNC connector
   - Use 12mm drill bit for standard BNC panel mount
   - Drill slowly to avoid cracking plastic
   - Clean up burrs with file or sandpaper

3. **Install BNC connector:**
   - Insert BNC panel mount through hole
   - Tighten nut on inside
   - Test fit with pH probe (should be snug but removable)

4. **Plan cable entry (optional):**
   - If you want charging port accessible, drill small hole for USB cable
   - Or: remove battery for charging

### Step 2: Test Components (15 min)

**CRITICAL: Test everything before assembly!**

1. **Test ESP32-S3:**
   - Connect to computer via USB
   - Upload a blink sketch
   - Verify it works
   - Note the GPIO pins for I2C (8 and 9)

2. **Test Atlas pH OEM:**
   - Connect to 3.3V power:
     ```
     Power Supply → VCC (Atlas)
     Power Ground → GND (Atlas)
     ```
   - Blue LED should light up
   - Wait 1 minute for startup
   - Measure voltage on TX/RX (should be present)

3. **Test battery:**
   - Measure voltage (should be 3.7-4.2V)
   - Check polarity (red = positive, black = negative)
   - Verify connector matches ESP32

### Step 3: Wire I2C Connection (20 min)

**Option A: Removable (Jumper Wires)**

Recommended for first build - easier to troubleshoot.

1. **Prepare jumper wires:**
   - Cut 4 female-female jumpers to ~10cm length
   - Strip 5mm from each cut end
   - Tin with solder (optional)

2. **Connect to ESP32:**
   ```
   ESP32-S3        Wire Color (suggested)
   ──────────────────────────────────────
   GPIO 8 (SDA)  → Blue wire
   GPIO 9 (SCL)  → Yellow wire
   3.3V          → Red wire
   GND           → Black wire
   ```

3. **Connect to Atlas pH OEM:**
   ```
   Atlas OEM     Wire Color
   ─────────────────────────
   SDA          ← Blue wire (from ESP32 GPIO 8)
   SCL          ← Yellow wire (from ESP32 GPIO 9)
   VCC          ← Red wire (from ESP32 3.3V)
   GND          ← Black wire (from ESP32 GND)
   ```

4. **Add strain relief:**
   - Bundle wires together
   - Use zip tie or tape
   - Add small dot of hot glue at connection points (optional)

**Option B: Permanent (Soldered)**

Only if you're confident everything works!

1. Cut wires to exact length needed
2. Solder to ESP32 pins (or use screw terminals if available)
3. Solder to Atlas OEM circuit
4. Add heat shrink to all connections
5. Test continuity with multimeter

### Step 4: Atlas to BNC Connection (10 min)

The Atlas pH OEM has a BNC connector for the probe.

1. **Connect probe to BNC:**
   - Screw probe BNC into Atlas OEM BNC connector
   - Hand-tighten only (don't over-torque)

2. **Route probe cable:**
   - Probe cable goes from Atlas OEM → through enclosure → external BNC
   - OR use BNC extension cable
   - OR mount Atlas near BNC hole so probe directly connects

**Best Practice:** Mount Atlas circuit near the BNC hole, connect probe directly through BNC panel mount to Atlas.

### Step 5: Mount Components (15 min)

1. **Layout components in enclosure:**
   - ESP32 on one side
   - Atlas circuit near BNC hole
   - Battery underneath (not on top of boards)
   - Leave room for air circulation

2. **Mounting methods:**
   
   **Option A: Hot glue** (removable)
   - Small dots on corners of boards
   - Don't cover components
   - Can be removed with heat if needed
   
   **Option B: Double-sided foam tape**
   - Clean surfaces with alcohol
   - Apply tape to board backs
   - Press firmly into enclosure
   
   **Option C: Screws and standoffs** (most professional)
   - Drill mounting holes
   - Use M2 or M3 screws and standoffs
   - Secure boards firmly

3. **Secure battery:**
   - Place under boards
   - Use foam tape or velcro
   - Ensure it can't short against components
   - Leave JST connector accessible

### Step 6: Waterproofing (10 min)

1. **Seal BNC connector:**
   - Apply silicone sealant around BNC threads
   - Fill gap between BNC and enclosure
   - Let cure 24 hours

2. **Seal USB port (if external):**
   - Use rubber grommet
   - Seal with silicone
   - Or use waterproof USB connector

3. **Check enclosure gasket:**
   - Clean mating surfaces
   - Ensure O-ring or gasket is seated
   - Apply thin bead of silicone if needed

### Step 7: Program and Test (10 min)

1. **Upload sketch:**
   - Connect ESP32 to computer (before sealing!)
   - Upload pHloat_Sensor.ino
   - Watch serial monitor for boot messages

2. **Initial configuration:**
   - Hold BOOT button while powering on
   - Connect to WiFi AP
   - Configure device name and relay MAC

3. **Test reading:**
   - Place probe in pH 7 buffer
   - Wait for reading in serial monitor
   - Should see pH near 7.0 (uncalibrated)

4. **Test deep sleep:**
   - Watch serial monitor
   - Should see "Going to sleep..." every 60 seconds
   - Verify LED flashes briefly each minute

### Step 8: Final Assembly (5 min)

1. **Disconnect USB cable**
2. **Connect battery to ESP32**
3. **Close enclosure**
4. **Tighten all screws**
5. **Add label with device name**
6. **Attach pH probe to BNC**

**✓ pH Sensor Complete!**

---

## Part 2: Relay Assembly

**Estimated Time:** 20-30 minutes

### Step 1: Prepare Enclosure (Optional)

If using an enclosure:

1. Drill hole for USB cable
2. Install cable grommet
3. Mount ESP32 with standoffs or adhesive

If not using enclosure:
- Just keep ESP32 on desk
- Make sure it won't get wet

### Step 2: Flash Firmware (15 min)

1. **Connect ESP32 to computer:**
   - Use USB cable
   - Select correct COM port in Arduino IDE

2. **Upload sketch:**
   - Open pHloat_Relay.ino
   - Ensure pHloat_Relay_WebUI.ino is in same folder
   - Click Upload
   - Wait for "Done uploading" message

3. **Open serial monitor:**
   - Set baud rate to 115200
   - Press RESET button on ESP32
   - Watch for MAC address - WRITE THIS DOWN!
   - Example: `Relay MAC Address: AA:BB:CC:DD:EE:FF`

### Step 3: Initial Configuration (10 min)

1. **Connect to relay AP:**
   - WiFi network: `pHloat-Relay`
   - Password: `phloat123`

2. **Access web interface:**
   - Open browser to `192.168.4.1`
   - You should see pHloat Dashboard

3. **Configure WiFi:**
   - Click "Configuration"
   - Enter WiFi SSID and password
   - Enter timezone offset (e.g., -18000 for EST)
   - Save
   - Relay will reboot and connect to WiFi

4. **Get IP address:**
   - Check serial monitor for IP address
   - Or check your router's DHCP client list
   - Bookmark this IP for easy access

### Step 4: Install in Permanent Location (5 min)

1. **Choose location:**
   - Near WiFi router for good signal
   - Protected from moisture
   - Accessible for maintenance
   - Near power outlet

2. **Mount relay:**
   - Screw enclosure to wall, or
   - Place on shelf securely

3. **Connect power:**
   - Plug in USB power supply
   - Verify power LED is on
   - Check web interface is accessible

**✓ Relay Complete!**

---

## Part 3: System Integration

### Link Sensors to Relay (10 min per sensor)

1. **Get relay MAC address:**
   - From serial monitor, or
   - From web interface → Status page

2. **Configure each sensor:**
   - Power on sensor while holding BOOT button
   - Connect to sensor's WiFi AP: `pHloat-XXXXXXXX`
   - Open browser to `192.168.4.1`
   - Enter device name (unique per sensor)
   - Enter relay MAC address
   - Save and reboot

3. **Verify communication:**
   - Check relay serial monitor
   - Should see data received from sensor
   - Check web interface → Data Review
   - Data files should appear

### Calibrate Sensors (15 min per sensor)

See Calibration section in README.md for detailed procedure.

Quick steps:
1. Access relay web interface
2. Go to Calibration page
3. Select sensor
4. Place probe in pH 7, 4, then 10 buffers
5. Enter readings
6. Save

---

## Assembly Tips & Tricks

### General Tips

1. **Test before sealing:**
   - Always test everything before closing enclosure
   - Much easier to fix issues when you can access components

2. **Label everything:**
   - Label sensors with device names
   - Note MAC addresses on enclosures
   - Keep a spreadsheet of sensor info

3. **Take photos:**
   - Photo of wiring before closing enclosure
   - Helps with troubleshooting later
   - Helps when building more sensors

4. **Build one first:**
   - Get one sensor working perfectly
   - Learn from mistakes
   - Then build the rest

### Common Mistakes to Avoid

❌ **Reversed I2C connections** (SDA/SCL swapped)
   - ✓ Double-check pinout before powering on

❌ **Wrong voltage** (5V instead of 3.3V to Atlas)
   - ✓ Atlas OEM is 3.3V only! Check twice!

❌ **Forgot to configure sensor**
   - ✓ Must enter config mode and set relay MAC

❌ **Probe dried out during assembly**
   - ✓ Keep probe in storage solution until ready to use

❌ **Battery installed backwards**
   - ✓ Check polarity! Red = positive, Black = ground

❌ **Sealed enclosure before testing**
   - ✓ ALWAYS test fully before sealing

### Troubleshooting Assembly Issues

**LED doesn't light on Atlas:**
- Check power connections
- Verify 3.3V at VCC pin
- Check for shorts

**ESP32 won't program:**
- Try different USB cable
- Press and hold BOOT while clicking Upload
- Check driver installation

**Probe not detected:**
- Check BNC connection
- Verify probe is Atlas-compatible
- Try different probe

**Battery won't charge:**
- Check polarity
- Verify charging circuit on ESP32
- Try different battery

---

## Maintenance Schedule

### After Assembly

- [ ] Test for 24 hours before deploying
- [ ] Verify readings are reasonable
- [ ] Confirm data uploads to Sheets (if configured)
- [ ] Test battery life (should last 60+ days)

### Monthly

- [ ] Clean pH probe
- [ ] Check battery voltage
- [ ] Verify calibration
- [ ] Download data backup

### Every 3 Months

- [ ] Recalibrate pH sensors
- [ ] Check enclosure seals
- [ ] Clean probe thoroughly
- [ ] Update firmware if available

### Yearly

- [ ] Replace probe (if degraded)
- [ ] Replace battery (if capacity low)
- [ ] Full system check

---

## Final Checklist

Before deploying your pHloat system:

### pH Sensor
- [ ] All I2C connections secure
- [ ] Battery charged and connected
- [ ] Enclosure properly sealed
- [ ] BNC connector waterproofed
- [ ] Firmware uploaded
- [ ] Device name configured
- [ ] Relay MAC address set
- [ ] Taking readings every 60 seconds
- [ ] Data appearing on relay
- [ ] Probe in storage solution when not measuring

### Relay
- [ ] Firmware uploaded
- [ ] WiFi configured and connected
- [ ] Web interface accessible
- [ ] Receiving data from sensors
- [ ] Storing data locally
- [ ] Google Sheets configured (if desired)
- [ ] Mounted in permanent location
- [ ] Power supply reliable

### System
- [ ] All sensors calibrated
- [ ] Data matching Tilt readings (if applicable)
- [ ] Backup relay available (recommended)
- [ ] Spare batteries charged
- [ ] Calibration buffers stocked
- [ ] Documentation printed/saved
- [ ] Team trained on system

**Congratulations! Your pHloat system is ready to brew! 🍺**
