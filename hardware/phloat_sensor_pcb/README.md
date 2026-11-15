# pHloat sensor PCB, rev A

**Status (2026-11-14): generated and DRC-checked in KiCad 10.0.8. Not fabricated, not assembled, not tested.**

External pH node: XIAO ESP32-S3 + Atlas pH OEM + SMA probe jack on the front, 18650 holder on the back. 118 x 32 mm, 2 layers.

## Files

| File | What it is |
|---|---|
| `gen_pcb.py` | Source of truth: parts, netlist, placement, routing. Regenerates the board. |
| `phloat_sensor.kicad_pro` | KiCad project. Open this. |
| `gen_sch.py` | Builds the schematic from the same netlist table, using labels instead of drawn wires. |
| `phloat_sensor.kicad_sch`, `phloat_sensor_schematic.pdf` | Generated schematic and its PDF. |
| `check_netlist.py` | Fails if the schematic netlist and `gen_pcb.NETS` ever differ. |
| `phloat_sensor.kicad_pcb` | Generated board. Open in KiCad to inspect; hand edits are lost on regeneration. |
| `phloat.kicad_sym`, `seeed_xiao.kicad_sym` | Project symbols (ours + Seeed's XIAO, CC-BY-SA-4.0) and the Seeed source library. |
| `phloat.pretty/` | `Atlas_pH_OEM` (ours) and `XIAO-ESP32-S3-SMD` (Seeed, CC-BY-SA-4.0, from github.com/Seeed-Studio/OPL_Kicad_Library). |
| `fab/` | Gerbers, drill files, pick-and-place CSV. |
| `render_top.png`, `render_bottom.png` | 3D renders. |

The `NETS` table in `gen_pcb.py` is the single source for both the schematic and the board.

## Rebuild and check

```
"C:\Program Files\KiCad\10.0\bin\python.exe" gen_pcb.py
"C:\Program Files\KiCad\10.0\bin\python.exe" gen_sch.py
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --severity-all phloat_sensor.kicad_pcb
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --severity-all phloat_sensor.kicad_sch
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch export netlist --format kicadsexpr -o sch.net phloat_sensor.kicad_sch
"C:\Program Files\KiCad\10.0\bin\python.exe" check_netlist.py sch.net
```

Expected DRC result: 0 unconnected items; 5 `copper_edge_clearance` errors, all on J1 (edge-mount SMA pads reach the board edge by design); the rest are silkscreen warnings.

Expected ERC result: one `lib_symbol_mismatch` warning on Q1 (the embedded AO3401A symbol is a flattened copy).

Expected parity result (`pcb drc --schematic-parity`): 22 `net_conflict` warnings, all for deliberately unconnected pads that the schematic names `unconnected-...`.

The schematic drawing has not been looked at by eye; expect overlapping labels that need tidying in eeschema.

## Pin map (firmware must match)

| XIAO pin | GPIO | Net | Purpose |
|---|---|---|---|
| D3 | 4 | SDA | I2C data to OEM (0x65) |
| D4 | 5 | PH_PWR | Drive HIGH to power the OEM and the I2C pull-ups; float/LOW in deep sleep |
| D5 | 6 | SCL | I2C clock |
| D8 | 7 | BAT_SENSE | Cell voltage / 2 (470k/470k, 100n) |
| BAT+ pad (underside) | - | VBAT | Cell + after reverse-polarity FET |

`Wire.begin(4, 6)`. These are not the XIAO default I2C pins; they were chosen so the board routes without crossings.

## Circuit

- **Power:** 18650 + -> Q1 (P-FET, gate to GND: blocks a reversed cell) -> XIAO BAT+ pad. The XIAO regulator makes 3.3 V. No charging path is intended; swap cells.
- **OEM power gating:** OEM VCC, both 4.7k pull-ups, C1 and C2 hang off GPIO5. R5 (100k) holds the rail low when the GPIO floats. OEM draws about 3.5 mA at 3.3 V (datasheet V4.7 p6).
- **Probe:** SMA centre -> OEM pin 4 by a 7.5 mm, 0.4 mm trace. SMA shell -> OEM pin 5 (`PRBG`). `PRBG` has its own pour on both layers around the probe trace and is never connected to `GND` (datasheet p33-34).
- **OEM pins 2, 9, 10 (NC) and 7 (INT)** are left floating as the datasheet requires. No vias under the module.

## BOM

| Ref | Part | Notes |
|---|---|---|
| U1 | Seeed XIAO ESP32-S3 | Soldered flat (castellations + underside BAT pads). Not the "Plus" or "Sense". |
| U2 | Atlas Scientific pH OEM | Reflow or hot air. Remove all flux afterwards (datasheet p4). |
| J1 | Amphenol 132289 SMA edge-mount jack | For 1.6 mm board |
| BT1 | Keystone 1042 18650 holder | Back side |
| Q1 | AO3401A (SOT-23 P-MOSFET) | Any logic-level P-FET, Vgs(th) under 1.5 V, pinout G-S-D = 1-2-3 |
| R1, R2 | 4.7k 0805 | I2C pull-ups |
| R3, R4 | 470k 0805 | Battery divider |
| R5 | 100k 0805 | PH_PWR pull-down |
| C1, C3 | 100n 0805 | |
| C2 | 1u 0805 | |
| H1-H4 | M2.5 holes | |

Off-board: Atlas Lab Grade pH probe (ENV-40-pH, male SMA, $99.99) and Atlas Tri-Clamp Probe Pipe Fitting (1.5", NSF-51, $34.99). Prices as listed on atlas-scientific.com on 2026-11-14.

## Check before ordering boards

1. **OEM footprint.** Print the board 1:1 and lay the module on it. Pad pitch is 2.25 mm (Atlas DXF averages 2.25; datasheet says 2.3). Confirm pin 1 (SDA) is at the silkscreen dot, top-left with the probe pins facing the SMA jack.
2. **XIAO BAT pads.** Confirm the two underside battery pads on your XIAO line up with pads 23/24 of the Seeed footprint.
3. **Protected 18650 length.** The Keystone 1042 is sized for bare cells; many protected cells (67-69 mm) will not fit. Firmware must stop transmitting below about 3.2 V because there is no hardware under-voltage cut-off.
4. **Under-module vias.** One GND via sits under the XIAO at (111.3, 11.55) mm from the board's top-left corner. Order tented vias.
5. **Seeed footprint licence** is CC-BY-SA-4.0. Fine for prototypes; check the terms before shipping a commercial design that includes it.

## Not on this board

- No temperature sensor: beer temperature comes from the Tilt over BLE.
- No galvanic isolation: the node is battery powered and floating. Do not take readings with USB plugged into a grounded computer and expect them to be accurate.
- No conformal-coat keep-outs are marked. Mask J1, the 18650 contacts and the XIAO USB-C port before coating. If you coat the OEM module, use clear coating only (datasheet p37).
