# Fermenter controller PCB, rev A

**Status (2026-11-15): board generated and DRC-checked in KiCad 10.0.8 (0 errors, 0 unconnected; remaining warnings are silkscreen). Schematic generated; its netlist matches the board (13 nets, 58 pins). Top render viewed; the schematic drawing has not been looked at by eye. Not fabricated, not assembled, not tested.**

Carrier for a XIAO ESP32-S3 that drives two 12 V DC pumps and reads up to four DS18B20 probes. 92 x 62 mm, 2 layers. Firmware: `esphome/fermenter_controller.yaml`. Enclosure: `../controller_enclosure/`.

## Files

| File | What it is |
|---|---|
| `gen_pcb.py` | Source of truth: parts, netlist, placement, routing. Regenerates the board. |
| `fermenter_controller.kicad_pro` | KiCad project. Open this. |
| `gen_sch.py` | Builds the schematic from the same netlist table, reusing the sensor board's generator. |
| `fermenter_controller.kicad_sch`, `fermenter_controller_schematic.pdf` | Generated schematic and its PDF. |
| `phloat.kicad_sym`, `sym-lib-table`, `fp-lib-table` | Project symbol library and the tables that point KiCad at it. |
| `fermenter_controller.kicad_pcb` | Generated board. Hand edits are lost on regeneration. |
| `fab/` | Gerbers, drill files, pick-and-place CSV. |
| `render_top.png`, `render_bottom.png` | 3D renders. |

```
"C:\Program Files\KiCad\10.0\bin\python.exe" gen_pcb.py
"C:\Program Files\KiCad\10.0\bin\python.exe" gen_sch.py
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --severity-all fermenter_controller.kicad_pcb
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --severity-all fermenter_controller.kicad_sch
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch export netlist --format kicadsexpr -o sch.net fermenter_controller.kicad_sch
"C:\Program Files\KiCad\10.0\bin\python.exe" ..\phloat_sensor_pcb\check_netlist.py sch.net .
```

Expected ERC result: two `power_pin_not_driven` errors on U2 (its supply and ground pins), because the supply arrives through a terminal block and the drawing has no power-flag symbols; and two `lib_symbol_mismatch` warnings from flattened library symbols. Expected netlist check: `netlist OK: 13 nets, 58 pins match gen_pcb.NETS`.

The schematic connects pins with named labels, not drawn wires, and has not been looked at by eye; expect overlapping labels.

## Connections

| Terminal | Pins (as printed on the board) | Use |
|---|---|---|
| J1 | + / - | 12 V DC supply |
| J2 | + / - | Cooling pump |
| J3 | + / - | Warming pump |
| J4-J7 | GND, DQ, 3V3 | DS18B20 probes: coolant, warm fluid, ambient, thermowell (all on one bus; any probe works in any terminal) |

| XIAO pin | GPIO | Net |
|---|---|---|
| D3 | 4 | DQ (1-Wire, 4.7k pull-up R5) |
| D4 | 5 | Cooling pump PWM |
| D5 | 6 | Warming pump PWM |
| 5V | - | From the on-board regulator through D3 |

## Circuit

- **Supply:** J1 -> 5x20 mm fuse F1 -> fused 12 V rail. D4 (TVS) clamps spikes and, on a reversed supply, conducts and blows the fuse. C1 is bulk capacitance for the pumps.
- **Logic power:** U2 (Traco TSR 1-2450 switching regulator, drop-in SIP-3) makes 5 V. D3 feeds the XIAO's 5V pin and stops USB back-feeding the rail, so USB can be plugged in with 12 V present.
- **Pumps:** low-side switched by Q1/Q2 (AO3400A). R1/R2 are 100 ohm gate resistors. **R3/R4 (10k) pull the gates low, so both pumps are off whenever the XIAO is booting, resetting, unpowered or absent.** D1/D2 are flyback diodes.

## Limits

- **12 V pumps only.** The FETs are 30 V parts and the TVS is sized for 12 V. Do not use a 24 V supply.
- **About 2 A per pump.** Set by the SOT-23 FETs and 1.5 mm switch traces. Fuse F1 at 5 A or less.
- The pumps must tolerate PWM on their supply (brushed DC pumps do; many brushless ones don't).

## BOM

| Ref | Part |
|---|---|
| U1 | Seeed XIAO ESP32-S3 (soldered flat; not Plus or Sense) |
| U2 | Traco TSR 1-2450 |
| Q1, Q2 | AO3400A (SOT-23 N-MOSFET, pinout G-S-D = 1-2-3) |
| D1, D2 | SS34 (SMA Schottky) |
| D3 | B5819W (SOD-123 Schottky) |
| D4 | SMBJ15A (SMB TVS, unidirectional, cathode to +) |
| F1 | 5x20 mm fuse clips (Littelfuse 111 series) + fuse |
| C1 | 220 uF 25 V radial, 8 mm, 3.5 mm pitch |
| C3 | 22 uF 10 V 0805 |
| R1, R2 | 100 ohm 0805 |
| R3, R4 | 10k 0805 |
| R5 | 4.7k 0805 |
| J1-J3 | Phoenix MKDS 1,5/2-5,08 |
| J4-J7 | Phoenix PT 1,5/3-3,5-H |
| H1-H4 | M3 holes |

## Check before ordering

1. **Diode polarity.** D1, D2, D4: cathode (pad 1) is on the +12 V side in the netlist. Confirm against the silkscreen when placing; a reversed flyback diode is a dead short across the supply.
2. **XIAO footprint** is Seeed's (CC-BY-SA-4.0). One GND via sits under the module at (85.3, 26.4) mm from the board's top-left: order tented vias.
3. **Terminal block orientation.** Wire entries should face the board edges (probes top, power left, pumps bottom). Check the first board before soldering all seven.
4. **TSR 1-2450 pinout** is 1 = Vin, 2 = GND, 3 = Vout as in the KiCad footprint; confirm on the part you buy.
