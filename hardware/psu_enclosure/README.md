# Power supply enclosure, rev A

**Status (2026-11-15): modelled in OpenSCAD and exported to STL (both parts valid solids). Renders of both sides viewed. Not printed, not fit-checked, not wired, not tested. The mains inlet cutout and the fan hole pattern use typical dimensions, not datasheets. The temperature figures below are calculations, not measurements.**

**This box contains mains voltage. If you are not comfortable wiring mains, have someone who is do it, or use a sealed, pre-wired 12 V supply and skip this box.**

A box for a bought 12 V 10 A enclosed switching power supply (the perforated metal "LED driver" type, 200 x 98 x 42 mm). A standard C13 computer power cable plugs into an IEC C14 inlet on one end; 12 V leaves through a cable gland to the fermenter controller. Two small fans move air through it. It is a separate box from the controller on purpose, so mains never enters the controller's enclosure.

Outside 282 x 124 x 89 mm, 146 mm wide over the mounting ears.

**Printer size: the body is 282 mm long.** It does not fit a 250 to 256 mm print bed, even diagonally. It needs a printer with a bed of about 300 mm or more.

| File | What it is |
|---|---|
| `psu_enclosure.scad` | Parametric source. Fit knobs at the top. |
| `psu_body.stl`, `psu_lid.stl` | Print files. Print the lid upside down (posts pointing up). |
| `preview.png` | Render from the intake side (grill low, near the mains inlet). |
| `preview_exhaust_side.png` | Render from the exhaust side (grill high at the far end; the round hole is the 12 V gland). |

## Cooling

Two 25 x 25 x 10 mm 12 V fans mount inside, against the two long side walls, each behind a slotted grill:

- **Intake:** low on one side wall, in the wiring bay at the mains-inlet end. This fan blows **into** the box.
- **Exhaust:** high on the opposite side wall, at the far end, standing just above the supply. This fan blows **out of** the box.

Air crosses the box diagonally along the whole length of the supply: under it (it sits on rails), over it, and through its own perforated case. Mounted on a wall with the inlet end down, that is bottom-in and top-out, the direction warm air rises anyway.

Every fan has an arrow moulded on its side showing which way it blows. Fit the intake with the arrow pointing into the box and the exhaust with the arrow pointing out. Two fans fighting each other move no air.

Set `fans = false` in the source for a sealed box with no grills.

## Parts to buy

| Part | Notes |
|---|---|
| 12 V 10 A enclosed switching supply | The one you chose. Check its label for the real input current. |
| IEC C14 inlet module with rocker switch and fuse holder, screw-mount | Gives you a plug, an on/off switch and a mains fuse in one part. |
| 5 x 20 mm fuse, slow-blow ("T") | Sized from the supply's label; T3.15 A is a typical value for a 120 W supply on 110 V. Slow-blow because these supplies draw a large surge at switch-on. |
| 2 x 25 x 25 x 10 mm 12 V fans | The ones you chose (0.1 A each). |
| 8 x M2.5 screws, about 16 mm, with nuts | Fan mounting: through the wall and the fan. Check the fan's hole size first. |
| M16 cable gland | For the 12 V output cable. |
| Mains-rated wire, 18 AWG (1.0 mm2) or heavier, in three colours | Inlet to supply. |
| Insulated crimp spade connectors (to suit the inlet's tabs) and fork or ferrule ends for the supply's screw terminals | Fully insulated ones on the mains side. |
| 2-core cable, 16 AWG (1.5 mm2) | 12 V to the controller. Heavy enough to survive the supply's full 10 A. |
| 2 x M3 screws, nuts and washers | Inlet mounting. |
| 10 x M3 heat-set inserts and screws, 2 mm O-ring cord (753 mm) | Lid. |

## Wiring

| From | To |
|---|---|
| Inlet LIVE (through its switch and fuse) | Supply `L` |
| Inlet NEUTRAL | Supply `N` |
| Inlet EARTH | Supply earth terminal (the ground symbol) |
| Supply `+V` | Controller board J1 `+`, and the red wire of both fans |
| Supply `-V` (or `COM`) | Controller board J1 `-`, and the black wire of both fans |

1. **Earth is not optional.** The supply's metal case is earthed through that wire. Check with a meter that the inlet's earth pin has continuity to the supply's case before you ever plug it in.
2. **Set the supply's input voltage switch** (110 V / 220 V), if it has one, before first power-up. On the wrong setting it is destroyed, sometimes violently.
3. Keep the mains wires short and on the inlet side of the bay, and the 12 V wires on the gland side. Do not bundle them together. Keep every wire clear of the fan blades.
4. Fit the supply's plastic terminal cover if it has one.
5. The fans run whenever the supply is on. They take 0.2 A together, which leaves the supply's capacity essentially untouched.
6. With the lid off and power applied, the supply's terminals are live. Unplug the C13 cable before opening the lid, every time.

## Rules for a mains box in a brewery

- **Plug it into a GFCI outlet.** This matters more than anything else here.
- **Mount it with the inlet facing down** and leave a drip loop in the power cable, so water running down the cable or the box drips off instead of into the connector. The IEC inlet and plug are not waterproof. In that position both grills face sideways, not up.
- **Mount it away from splash and hose-down**, above floor level. With grills it is no longer a sealed box: water sprayed at a grill goes straight onto mains electronics.
- **Print it in a flame-retardant material** (a filament rated UL 94 V-0, for example flame-retardant ABS, PC or PETG). Do not use PLA: it softens at the temperatures a power supply reaches.

## What the fans cost you

A fan-cooled box breathes the room's air. In a brewery that air is damp and sometimes carries cleaning-chemical vapour, and the fans pull it across mains electronics. Over time that can mean condensation and corrosion inside the supply. The sealed version (`fans = false`) avoids that but must be kept to about half the supply's rating. If the box will live in the brewhouse itself, the sealed version at 5 A is the safer one; in a drier utility space, the fans are fine.

## Heat

The controller board is limited to about 2 A per pump, so in this system the supply should not deliver more than about 5 A (60 W), where it wastes roughly 10 W as heat.

| Version | At 5 A (this system) | At the full 10 A |
|---|---|---|
| Sealed (`fans = false`) | about 15 to 20 C above the room | roughly double: too hot for a printed box |
| With fans | about 5 to 8 C above the room | about 11 to 17 C above the room |

These are estimates from surface area and an assumed 1 to 2 cubic feet per minute actually getting through the grills. The fan's real airflow is not given in its listing. On first use, run both pumps for an hour and check the box is only warm to the touch.

## Measure before printing

1. **The inlet module.** Cutout (`inlet_cut_w` x `inlet_cut_h`, default 27.5 x 47.5 mm), screw spacing (`inlet_screw_pitch`, 40 mm), front flange height (`inlet_flange_h`, 60 mm) and depth behind the panel (`inlet_depth`, 35 mm). The defaults are typical for a fused, switched C14 module; yours may differ.
2. **The fans.** Hole spacing (`fan_pitch`, 20 mm), hole size (`fan_screw_d`, 3.0 mm clearance for M2.5), body (`fan_size`, 25 mm) and thickness (`fan_t`, 10 mm). Typical for a 25 mm fan; check yours.
3. **The supply.** `psu_l`, `psu_w`, `psu_h` (200 x 98 x 42 mm from the listing; listings round).
4. **Which end the supply's terminals are on.** The model assumes one short end, facing the wiring bay.
5. **The gland nut** (`dc_gland_nut`, 24 mm across corners).

The model refuses to export if the inlet's flange would not sit on flat wall, if the wiring bay is too short for the inlet or the intake fan, if a fan grill would run off the flat wall, if the exhaust fan would hit the supply, or if the gland nut would foul the base or the rim.

## How the supply is held

It rests on two floor rails (air passes underneath), is centred by ribs on the side walls, stopped at both ends, and held down by four posts under the lid that sit 0.5 mm above it. It is not screwed down, so the box does not depend on the supply's mounting-hole pattern.

## Not included

- No filter on the intake. A scrap of fan filter foam behind the intake grill would keep dust out.
- No drip hoods over the grills.
- No power indicator. Many of these supplies have their own green LED, which the lid hides.
- No safety certification of any kind. This is a home-built mains enclosure.
