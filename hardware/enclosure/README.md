# pHloat sensor enclosure, rev A

**Status (2026-11-14): modelled in OpenSCAD and exported to STL. Not printed, not fit-checked, not leak-tested.**

A two-part box for the rev A sensor PCB. Outside size 184 x 54 x 43 mm, 206 mm long over the mounting ears.

| File | What it is |
|---|---|
| `phloat_enclosure.scad` | Parametric source. Change the fit knobs at the top, then re-export. |
| `phloat_body.stl`, `phloat_lid.stl` | Print files. |
| `preview.png`, `preview_body.png` | Renders. |

## How it goes together

- The PCB sits component-side down on four posts (M2.5 self-tapping screws). The 18650 faces the lid, so taking the lid off is all a cell swap needs.
- The lid seals on a 2 mm O-ring cord in a groove around the rim. Cord length on the groove centreline: 417 mm. Eight M3 screws into heat-set inserts, all outside the O-ring.
- One penetration: an M16 cable gland on the end wall, on the SMA axis. The probe's SMA plug passes through the gland; the gland seals on the cable.
- A 45 mm bay past the SMA jack leaves room for the plug and the cable bend.

## Mounting

Two flat ears on each end, flush with the base, each with a 4.5 mm hole for an M4 screw or a zip tie. The holes sit 12 mm out from the wall so a screwdriver clears the rim. Set `mount_ears = false` in the source for a plain box.

## Measure before printing

1. **`batt_h` (22 mm):** PCB surface to the top of an 18650 sitting in the Keystone 1042. I did not have the holder height from a datasheet.
2. **`gland_d` (16.2 mm) and the gland's clamping range:** the Atlas probe cable diameter is not published on the product page. If the cable is thinner than the gland's minimum, add a reducing grommet or change to a split-seal gland.
3. **`post_h` (12 mm):** must clear the gland's inside nut and the mated SMA plug.
4. **O-ring squeeze:** the groove is 2.6 wide x 1.5 deep for 2.0 mm cord. Print one corner as a test piece first.

## Material

The box is outside the fermenter and never touches the beer, so it does not need a food-contact material. Use PETG or ASA for splash and sanitiser resistance. The food-contact parts are the probe and the Atlas tri-clamp fitting (NSF-51).

## Not included

- No light pipe or window, and no external USB port: programming and charging mean opening the lid.
