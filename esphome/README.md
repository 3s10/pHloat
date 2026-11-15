# pHloat ESPHome firmware (rev A PCB)

**Status (2026-11-15): `esphome config` and `esphome compile` both pass on ESPHome 2026.10.2 (ESP-IDF 5.5.6, 73% flash). Not flashed, not tested on hardware.**

Replaces the Arduino sensor + relay sketches for the rev A board. The node joins Wi-Fi itself, so there is no relay and no ESP-NOW.

| File | What it is |
|---|---|
| `phloat.yaml` | Device config. Knobs are in `substitutions` at the top. |
| `components/ph_oem/` | Driver for the Atlas pH OEM (I2C 0x65, register-based). |
| `secrets.yaml.example` | Copy to `secrets.yaml` (gitignored) and fill in. |

## Each wake

1. Power the pH module (GPIO5), check the cell; below `battery_cutoff` it sleeps until the cell is swapped.
2. Listen for the configured Tilt colour over BLE (gravity, temperature).
3. Send the Tilt temperature to the pH module, read pH.
4. POST to the pHloat server on the Tilt Pi (`X-pHloat-Token` header, `integration/upload_contract.json`).
5. Publish to Home Assistant over the native API, then deep sleep for `sleep_time`.

A fresh power-up stays awake for `maintenance_time` with live pH every 5 s: calibrate from the Home Assistant buttons (mid first) and do OTA updates then.

## Build

```
pip install esphome
esphome config phloat.yaml
esphome compile phloat.yaml
esphome run phloat.yaml
```

Run these from PowerShell or cmd, not Git Bash: the ESP-IDF installer refuses MSys ("MSys/Mingw is not supported").

## Known gaps

- It builds, but nothing has run on a board: the pH driver, the Tilt parser and the wake cycle are untested.
- The Arduino sketches in `pHloat_Sensor/` and `pHloat_Relay/` are untouched and still describe the old EZO + ESP-NOW design.
- Sleep current, PH_PWR floating low in deep sleep, and Tilt reception through stainless are unmeasured.
- Home Assistant keeping the last value while the node sleeps is expected behaviour for deep-sleep devices, not verified here.

---

# Fermenter controller (`fermenter_controller.yaml`)

**Status (2026-11-15): `esphome config` and `esphome compile` pass on ESPHome 2026.10.2 (73% flash), including the hub settings sync. No hardware exists: never flashed, no pump has ever turned, the control gains are starting guesses.**

One XIAO ESP32-S3 per fermenter. It pumps chilled fluid through the cooling jacket or warm water through the reactor rod to hold the beer at a target temperature. The loop runs on the board, so it keeps working with Wi-Fi, Home Assistant and the Pi all down. There is no mains voltage anywhere on this board: the warm water is heated by a separate UL-listed aquarium heater with its own thermostat.

## How it decides

1. **Beer temperature** comes from the Tilt over Bluetooth, or from an optional thermowell probe (`prefer_well_probe` picks which is first; the other is the backup). A Tilt silent for `tilt_timeout_s` counts as lost.
2. A **PID loop** turns the error into a pump speed: cooling pump above target, warming pump below, neither inside `deadband`.
3. A **guard**, once a second, is the only code that drives the pumps. It forces a pump to zero when:
   - there is no beer temperature (both pumps off);
   - the fluid's probe is missing;
   - the coolant isn't at least `min_delta` colder than the beer, or the warm fluid isn't at least `min_delta` warmer;
   - the warm fluid is hotter than `warm_fluid_max`;
   - heating and cooling are somehow both requested (both off).
   The reason shows in the "Control status" entity.

## Settings come from the hub

The hub on the Pi holds the master copy of every setting. Every 15 seconds the controller checks in over Wi-Fi: it reports the settings it is running, and the hub's reply says what they should be. The controller applies any that differ and saves them in flash, so it carries on alone with the last settings it was given. The controller makes the connection, so it needs no open port.

Settable from the hub's **Controllers** page: target temperature, mode (auto, cool, heat, off), dead zone, the three PID gains, the warm-fluid limit, the minimum fluid difference, the slowest pump speed, which Tilt to follow, the Tilt timeout, and whether the thermowell probe is preferred. Each has an allowed range that is checked on the hub and again on the controller.

Home Assistant shows everything (temperatures, pump speeds, status, the climate entity) for dashboards and alerts. A change made in Home Assistant is put back by the hub at the next check-in.

The values in `substitutions:` marked "first-boot values" are only used the first time the board starts.

## Wiring

| XIAO pin | GPIO | Goes to |
|---|---|---|
| D3 | 4 | DS18B20 data bus (all probes), one 4.7k pull-up to 3V3 |
| D4 | 5 | Cooling pump MOSFET gate |
| D5 | 6 | Warming pump MOSFET gate |
| 5V / GND | - | 5 V buck converter from the pump supply |

The rev A board in `hardware/controller_pcb/` implements this wiring (12 V pumps, about 2 A each). Per pump: logic-level N-MOSFET (fully on at 3.3 V gate, for example AO3400A up to about 3 A), low-side. 100 ohm gate resistor, **10k gate pull-down** (this is what keeps the pump off while the ESP boots, resets or is dead), Schottky flyback diode across the pump, fuse on the pump supply.

Probes: waterproof DS18B20 on the coolant line, the warm-fluid line, ambient air, and optionally a thermowell in the beer. Flash once, read each address from the boot log, paste into `substitutions`.

## Check before buying pumps

- **The pump must tolerate PWM speed control.** A brushed DC pump does. Many small brushless pumps have their own electronics and misbehave when their supply is chopped; those need a pump with a dedicated speed input instead.
- `pump_min` is the duty below which the pump stalls; find it on the bench.
- `pump_pwm_hz` is 1 kHz to start. Higher is quieter but needs a MOSFET that switches cleanly from a 3.3 V pin.

## Bench test before it goes near beer

1. No probes connected: status reads "OFF: no beer temperature", both gates at 0 V.
2. Hold the XIAO in reset: both pumps stay off (proves the pull-downs).
3. Beer probe in warm water, target set low, coolant probe in ice water: cooling pump runs, speed rises with the error.
4. Move the coolant probe into the warm water: "Cooling blocked: coolant not cold enough", pump stops.
5. Same two tests mirrored for warming, plus warm-fluid probe above `warm_fluid_max`: "Warming blocked: fluid too hot".
6. Unplug the beer probe and silence the Tilt mid-run: both pumps stop within `tilt_timeout_s`.
7. Turn the Wi-Fi off: control carries on.

## Not done

- The PCB (`hardware/controller_pcb/`) and enclosure (`hardware/controller_enclosure/`) are designed but not built.
- Gains are untuned. A fermenter responds over hours; expect to tune them on the hub's Controllers page.
- The PID autotune button prints its result in the log; type it into the hub, because the hub's gains replace it at the next check-in.
- The settings sync has only been tested on the hub side (automated test). No controller has ever checked in.
