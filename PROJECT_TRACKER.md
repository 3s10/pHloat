# pHloat project tracker

One place for every decision made and every piece of work planned. Tick items off as they are finished.

**Last updated: 2026-11-15.** No hardware has been built.

How to read the status marks:

- `[x]` done and checked on the development PC (tests pass, it compiles, or the design-rule check is clean)
- `[ ]` not done yet
- **Not proven on hardware** means exactly that: it builds or passes tests, but no real board, pump, probe or Pi has run it.

---

## 1. What the system is

| Part | What it does | Where it lives |
|---|---|---|
| **pHloat sensor** | Battery box on a tri-clamp port. Reads pH with an Atlas probe, reads the Tilt over Bluetooth, sends pH + gravity + temperature. Sleeps between readings. | `esphome/phloat.yaml`, `hardware/phloat_sensor_pcb/`, `hardware/enclosure/` |
| **Fermenter controller** | Mains-free box that runs two 12 V pumps (cooling jacket, warm-water reactor rod) to hold the beer at a target temperature. Works on its own. | `esphome/fermenter_controller.yaml`, `hardware/controller_pcb/`, `hardware/controller_enclosure/` |
| **Hub** | Raspberry Pi app. Logs every Tilt, stores everything in a database, shows the web pages, holds the master copy of controller settings, backs up to Google Drive. Replaces TiltPi. | `tiltpi/` |
| **Home Assistant** | Dashboards and alerts only. It is never the place settings are changed. | (your existing install) |

---

## 2. Decisions

Each decision is locked unless you change it. "Why" is the reason given at the time.

### Product and hardware

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-11-14 | The sensor is an **external box on a tri-clamp ferrule**, not a floating capsule. | Your call: stay with the existing external design. |
| D2 | 2026-11-14 | pH circuit is the **Atlas Scientific pH OEM** (I2C address 0x65). | Chosen over the analog Surveyor board for accuracy. |
| D3 | 2026-11-14 | Microcontroller is the **Seeed XIAO ESP32-S3** on both boards. | Small, has Wi-Fi and Bluetooth. |
| D4 | 2026-11-14 | Sensor power is a **swappable 18650 cell** on the back of the board; no charging circuit. | Simple: swap cells. |
| D5 | 2026-11-14 | Probe is the **Atlas Lab Grade pH probe** with the **Atlas tri-clamp probe fitting**. | Inexpensive, purchasable, NSF-51 fitting. |
| D6 | 2026-11-14 | **Beer temperature comes from the Tilt**; no temperature sensor on the pH board. | The Tilt is already in the beer. |
| D7 | 2026-11-14 | All wetted materials must be **food safe**, with **O-rings on every penetration**. | Product requirement. |
| D8 | 2026-11-15 | Heating uses a **warm-water reactor rod** (MoreBeer conical reactor rod), not an electric element in oil. | Removes mains voltage, oil and pressure from the fermenter. |
| D9 | 2026-11-15 | Warm water is heated by a **separate UL-listed aquarium heater**. Nothing we design touches mains. | Keeps electrical risk off our boards. |
| D10 | 2026-11-15 | One controller board drives **both pumps with variable speed** and reads the fluid temperatures. | Jacket and rod use the same hardware. |
| D11 | 2026-11-15 | Controller board is **12 V only, about 2 A per pump**. | Limits of the chosen transistors and traces. |

### Firmware

| # | Date | Decision | Why |
|---|---|---|---|
| D12 | 2026-11-14 | Firmware is **ESPHome**, replacing the Arduino sensor and relay sketches. | Native Home Assistant support. |
| D13 | 2026-11-14 | The sensor **reads the Tilt directly** and forwards its data with the pH. | Capture everything without opening the fermenter. |
| D14 | 2026-11-15 | The **control loop runs on the controller board**, not on the Pi. | It must hold temperature with the Pi and Wi-Fi down. |
| D15 | 2026-11-15 | **Fail-safe = both pumps off.** Lost sensor, bad fluid temperature, crash or reset all end there. | A fermenter tolerates hours without heating or cooling. |
| D16 | 2026-11-15 | **No ESP-NOW.** Devices use Wi-Fi to reach the hub and Bluetooth to hear the Tilt. | ESP-NOW added hardware and no benefit; you dropped it. |
| D17 | 2026-11-15 | The **hub is the master copy of controller settings**. The controller checks in every 15 s and applies them. | You want everything set from the hub. |

### Hub and data

| # | Date | Decision | Why |
|---|---|---|---|
| D18 | 2026-11-15 | The hub **replaces TiltPi** and reads Tilt broadcasts itself. | TiltPi has no local database. |
| D19 | 2026-11-15 | Database is **SQLite**. Move to Postgres only for multiple sites or pro customers. | One Pi, a few rows a minute. |
| D20 | 2026-11-15 | The Pi is **never reachable from the internet**. It only makes outbound connections. | Your security rule. |
| D21 | 2026-11-15 | **Home Assistant is dashboards and alerts only.** | Your rule. |
| D22 | 2026-11-15 | Backups: **weekly full copy + daily deltas**, keeping about two weeks, pushed to Google Drive. | The database will grow; don't upload all of it daily. |
| D23 | 2026-11-15 | **When a fermentation is marked complete:** export it, upload it to Drive and Google Sheets, verify the upload, then prune its readings from the database. | Keeps the live database small; the export is the long-term record. |
| D24 | 2026-11-15 | Recipes are **imported as files** (BeerXML or Brewfather export), not rebuilt in a recipe editor. | Don't rebuild recipe software. |
| D25 | 2026-11-15 | Manual measurements (pressure, dissolved oxygen) and process notes are **timestamped log entries**. | You'll record them by hand for now. |
| D26 | 2026-11-15 | **Deletes are soft**: recoverable for 7 days, then removed. | Protects against mistakes. |
| D27 | 2026-11-15 | The Tilt listener stores **one row per Tilt per minute** (adjustable), not every broadcast. | Every broadcast is about 86,000 rows a day per Tilt. |

### How we work

| # | Date | Decision |
|---|---|---|
| D28 | 2026-11-15 | All code is **commented block by block** so a first-year college student can follow and recreate it. |
| D29 | 2026-11-15 | This tracker records every decision and plan. |
| D31 | 2026-11-15 | The hub feeds Home Assistant by **calling Home Assistant's own web address** with an access token (no MQTT broker needed). Chosen by Jarvis as the option needing nothing extra installed; change it if you run MQTT. |
| D30 | 2026-11-15 | The **"preserve only, do not overwrite" rule stays** for the original root documents. Everything in current use is documented; legacy items that are not changing are left exactly as they are. |

---

## 3. Work done

### pHloat sensor

- [x] Sensor PCB designed (118 x 32 mm), design-rule check clean, fabrication files exported
- [x] KiCad project and schematic generated; schematic netlist matches the board
- [x] Sensor enclosure modelled and exported for printing
- [x] ESPHome firmware written; validates and compiles
- [x] Custom ESPHome driver for the Atlas pH OEM (read, temperature compensation, calibration)
- [ ] **Not proven on hardware:** no board made, no pH reading ever taken

### Fermenter controller

- [x] ESPHome firmware written: PID loop, safety guard, Tilt reading, probe reading
- [x] Controller PCB designed (92 x 62 mm), design-rule check clean, fabrication files exported
- [x] Controller enclosure modelled and exported for printing
- [x] Controller schematic generated; its netlist matches the board
- [x] Mounting ears added to both enclosures
- [x] Hub settings sync written into the firmware (check-in every 15 s)
- [x] Firmware with settings sync validates and compiles
- [ ] **Not proven on hardware:** no board made, no pump has turned, gains untuned

### Hub (Raspberry Pi)

- [x] Database: readings, devices, batches, log entries, controller settings
- [x] Intake: accepts pHloat and controller uploads with a secret token
- [x] Tilt listener (handles Tilt and Tilt Pro)
- [x] Web pages: overview, batch create/edit, log entries, devices, trash
- [x] Charts with hover values and drag-to-zoom
- [x] Rename devices; delete with 7-day recovery
- [x] Backups: weekly full + daily delta, pruning, restore, missing-delta warning
- [x] Mark complete: export, upload, verify, prune
- [x] Controllers page: see each controller, change every setting
- [x] Installer script rewritten
- [x] Recipe files read into a summary (BeerXML and Brewfather JSON); fills recipe name and yeast
- [x] Log entries can be edited
- [x] Tilt readings passed on to Home Assistant (off until `ha_url` and `ha_token` are set)
- [x] Older databases gain new columns automatically when opened
- [x] 27 automated tests pass
- [ ] **Not proven on hardware:** never run on a Pi; no Tilt heard; no Google Drive command ever run

---

## 4. Work planned

### Build and prove (needs real hardware)

- [ ] Order sensor PCBs (first check the pH module footprint 1:1 on paper)
- [ ] Order controller PCBs (first check diode polarity and terminal directions)
- [ ] Print both enclosures (first measure battery height, gland nuts, cable diameters)
- [ ] Install the hub on the Pi; stop TiltPi
- [ ] Prove the Tilt listener hears a real Tilt, including through a stainless fermenter
- [ ] Set up Google Drive with `rclone`; prove backup, restore and run upload for real
- [ ] Run a full restore drill onto a blank SD card
- [ ] Flash the sensor; calibrate the pH probe (mid, low, high)
- [ ] Measure sensor sleep current and work out real battery life
- [ ] Run the controller bench test (7 steps in `esphome/README.md`)
- [ ] Tune the controller's PID gains on a real fermenter
- [ ] Check the hub pages on a phone (never viewed at phone width)
- [ ] Look at the Controllers page and the recipe fold-out in a browser (tested, never viewed)
- [ ] Prove the Home Assistant feed against your real Home Assistant
- [ ] Upload a real Brewfather export and a real BeerXML file and check the summary
- [ ] Open both schematics in KiCad and tidy overlapping labels

### Software still to write

- [x] Hub publishes Tilt readings to Home Assistant
- [x] Parse recipe files into fields
- [x] Edit an existing log entry
- [x] Archived runs out of the weekly full backup: already covered, because archiving prunes a finished run's readings
- [x] Schematic drawing for the controller board
- [x] Mounting ears for both enclosures
- [ ] Power-flag symbols on the controller schematic, so its electrical check reports no errors
- [ ] DIN-rail clip for the controller enclosure (only if you mount on DIN rail)

### Documentation and housekeeping

- [x] Comment all current code block by block (D28); every build, test and design-rule check re-run afterwards
- [x] Component READMEs and the upload contract updated to the current design
- [x] `SYSTEM_GUIDE.md` written as the current starting point
- [x] Legacy documents and legacy code left untouched (D30). `SYSTEM_GUIDE.md` is the current starting point and says which files are legacy
- [x] Work committed to git and pushed to GitHub on branch `esphome-hub-controller` (2026-11-15)

### Later / product

- [ ] Pressure transducer in place of manual pressure entries
- [ ] Dissolved-oxygen sensor in place of manual entries
- [ ] Safety listing and certification work before selling
- [ ] Check the Seeed footprint licence (CC-BY-SA-4.0) before commercial use
- [ ] Multi-site support and Postgres (only if needed)

---

## 5. Known risks and unverified claims

| Risk | What would settle it |
|---|---|
| Tilt Bluetooth may not reach through a stainless fermenter | Test with a real Tilt in a real tank |
| The Google Drive upload flags were written from memory | First real `rclone` run |
| The Brewfather recipe field names were written from memory | Upload a real Brewfather export |
| Sensors pushed to Home Assistant vanish when it restarts, until the next Tilt reading | Watch a Home Assistant restart |
| A standard Tilt reports whole degrees F, so control from the Tilt alone is steppy | Fit a thermowell probe and prefer it |
| Sensor readings may be off while USB is plugged into a grounded computer (no isolation) | Compare readings on battery vs USB |
| Sensor sleep current is unmeasured, so battery life is unknown | Measure it |
| Many small brushless pumps misbehave on a chopped supply | Buy a brushed pump, or test the chosen one |
| Controller gland nut clearance is only 0.6 mm with the assumed nut size | Measure the glands before printing |
| The pH module footprint pitch (2.25 mm vs the datasheet's 2.3 mm) | Print 1:1 and lay the module on it |
| No hardware under-voltage cut-off on the sensor; firmware stops at 3.2 V | Test with a nearly flat cell |

---

## 6. Change log

| Date | What changed |
|---|---|
| 2026-11-14 | Reviewed the original design. Chose the hardware. Designed the sensor PCB and enclosure. Wrote the sensor firmware. |
| 2026-11-15 | Built the hub (database, Tilt listener, pages, backups, archive, trash, charts). Wrote the controller firmware. Designed the controller PCB and enclosure. Dropped ESP-NOW. Added hub-to-controller settings sync. Started this tracker. Commented all current code. Wrote SYSTEM_GUIDE.md. Added recipe reading, log editing, the Home Assistant feed, the controller schematic and mounting ears. Committed and pushed. |
