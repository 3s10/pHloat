# Fermenter controller enclosure, rev A

**Status (2026-11-15): modelled in OpenSCAD and exported to STL (both parts valid solids). Preview viewed. Not printed, not fit-checked, not leak-tested.**

Two-part box for the controller PCB. Outside 132 x 136 x 35 mm, 154 mm long over the mounting ears.

| File | What it is |
|---|---|
| `controller_enclosure.scad` | Parametric source. Fit knobs at the top. |
| `controller_body.stl`, `controller_lid.stl` | Print files. |
| `preview.png` | Render. |

## How it goes together

- The PCB sits component-side up on four posts (M3 self-tapping screws).
- Seven M12 cable glands: four on the probe side, three on the pump side (power, cooling pump, warming pump). Wiring bays on three sides give the wires room to bend into the terminals.
- The lid seals on a 2 mm O-ring cord (477 mm long) with eight M3 screws into heat-set inserts, all outside the seal.
- USB-C is reached with the lid off.

## Mounting

Two flat ears on each end, flush with the base, each with a 4.5 mm hole for an M4 screw or a zip tie. The holes sit 12 mm out from the wall so a screwdriver clears the rim. Set `mount_ears = false` in the source for a plain box.

## Measure before printing

1. **`gland_nut` (18 mm):** across the corners of your gland's nut. The model refuses to export if the nut would foul the base or the rim; with the defaults there is 0.6 mm to spare under the rim.
2. **`comp_h` (20 mm):** PCB top to lid. The tallest part is the 220 uF capacitor; measure yours.
3. **Cable diameters** against the gland's clamping range (M12 glands usually take 3-6.5 mm).
4. **O-ring squeeze:** print one corner as a test piece first.

## Not included

- No DIN-rail clip.
- No status light or window.
- Use PETG or ASA. The box never touches the beer.
