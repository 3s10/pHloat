# pHloat system guide

**Start here.** This describes the system as it is designed today (2026-11-15). The older documents in this folder (`README.md`, `START_HERE.md`, `WIRING.md`, `ASSEMBLY.md` and others) describe the original Arduino relay design and no longer match.

**Honest status:** everything below builds, compiles or passes its automated tests on the development PC. **No hardware has been built and nothing has run on a real board or Pi.** Decisions, finished work and the to-do list are in [`PROJECT_TRACKER.md`](PROJECT_TRACKER.md).

## What the system does

It records a fermentation in enough detail to repeat it: gravity, temperature and pH over time, the recipe, the fermenter used, and a timestamped log of everything done by hand. It can also hold the beer at a target temperature.

## The parts

```
   in the fermenter                on the fermenter               on the network
  +----------------+   Bluetooth   +------------------+   Wi-Fi   +----------------------+
  | Tilt           | ------------> | pHloat sensor    | --------> |                      |
  | hydrometer     |               | (battery, pH)    |           |  Hub (Raspberry Pi)  |
  | gravity + temp | ------+       +------------------+           |  database, web pages |
  +----------------+       |                                      |  backups, settings   |
                           |       +------------------+   Wi-Fi   |                      |
                           +-----> | Fermenter        | <-------> |                      |
                         Bluetooth | controller       |  readings +----------+-----------+
                                   | 2 pumps, probes  |  out,                |  outbound only
                                   +---+----------+---+  settings back       v
                                       |          |                    Google Drive
                              cooling jacket   reactor rod             (backups, finished runs)
                              (chilled fluid)  (warm water)

   Home Assistant reads the sensor and the controller directly, and the hub passes Tilt readings
   on to it. It is for dashboards and alerts only. The Tilt is also heard directly by the hub.
```

| Part | Job | Read next |
|---|---|---|
| **pHloat sensor** | Battery box on a tri-clamp port. Wakes every 15 minutes, reads the Tilt and the pH probe, sends both, sleeps. | [`esphome/README.md`](esphome/README.md), [`hardware/phloat_sensor_pcb/README.md`](hardware/phloat_sensor_pcb/README.md), [`hardware/enclosure/README.md`](hardware/enclosure/README.md) |
| **Fermenter controller** | Runs a cooling pump and a warming pump to hold the target temperature. Keeps working if the Pi or Wi-Fi is down. Fails safe: both pumps off. | [`esphome/README.md`](esphome/README.md) (second half), [`hardware/controller_pcb/README.md`](hardware/controller_pcb/README.md), [`hardware/controller_enclosure/README.md`](hardware/controller_enclosure/README.md) |
| **Hub** | The Raspberry Pi. Logs every Tilt, stores everything, serves the web pages, holds the master copy of controller settings, backs up to Google Drive. | [`tiltpi/README.md`](tiltpi/README.md) |

## Rules the design follows

1. **The Pi is never reachable from the internet.** It only makes outbound connections (backups).
2. **The hub is the master.** Settings are changed on the hub. Home Assistant is for dashboards and alerts.
3. **The controller works alone.** Its control loop runs on its own board, and it remembers its last settings.
4. **Fail-safe means both pumps off.** No beer temperature, a missing probe, fluid at the wrong temperature, a crash or a reset all end there.
5. **No mains voltage on any circuit we design, or inside the controller box.** Warm water comes from a separate UL-listed aquarium heater, and 12 V comes from a bought supply. That supply lives in its own printed box, which does contain mains wiring and has its own safety rules.
6. **Nothing is deleted until its copy is proven.** A finished run is exported, uploaded and verified before its readings are pruned.

## Where everything is

| Folder | Contents |
|---|---|
| `esphome/` | Firmware for both boards (`phloat.yaml`, `fermenter_controller.yaml`) and the pH chip driver |
| `tiltpi/` | The hub: web server, Tilt listener, backup tool, pages |
| `hardware/phloat_sensor_pcb/` | Sensor circuit board (generator script, KiCad files, fabrication files) |
| `hardware/enclosure/` | Sensor enclosure (OpenSCAD source, STL files) |
| `hardware/controller_pcb/` | Controller circuit board |
| `hardware/controller_enclosure/` | Controller enclosure |
| `hardware/psu_enclosure/` | Box for the 12 V power supply, with the mains inlet. **Contains mains: read its README first** |
| `integration/upload_contract.json` | The message format devices use to talk to the hub |
| `tests/` | Automated tests for the hub |
| `install-phloat-tiltpi.sh` | Installs the hub on a Raspberry Pi |
| `PROJECT_TRACKER.md` | Every decision, what is done, what is planned |

Not part of the current design: `pHloat_Sensor/`, `pHloat_Relay/`, `GoogleAppsScript.js`, `scripts/`, `web/` (the original Arduino relay system).

## How the code is written

Every current source file is commented block by block for a reader new to the subject: each file starts by saying what it is for and defining the words it uses, and each block says what it does and why. The circuit boards and enclosures are generated by scripts, so they can be recreated or changed by editing a script and re-running it.

## Order to build it in

1. **Hub first.** Install it on the Pi and confirm it hears a Tilt. It needs no custom hardware.
2. **Backups.** Set up Google Drive and prove a backup and a restore before trusting it with data.
3. **Sensor.** Order the board, print the box, flash, calibrate the probe.
4. **Controller.** Order the board, print the box, run the bench test, then tune on a real fermenter.

Each component's README lists what to measure or check before spending money on it.

## Checking the software on a PC

```
pip install flask bleak
python -m unittest discover tests                     # hub: 27 tests

pip install esphome                                   # run from PowerShell or cmd, not Git Bash
cd esphome
esphome compile phloat.yaml
esphome compile fermenter_controller.yaml
```

The circuit boards and enclosures have their own rebuild and check commands in their READMEs.
