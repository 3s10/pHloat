// Power supply enclosure, rev A. Units: mm.
//   openscad -D "part=\"body\"" -o psu_body.stl psu_enclosure.scad
//   openscad -D "part=\"lid\""  -o psu_lid.stl  psu_enclosure.scad
//
// WHAT THIS IS
//   A box for a bought 12 V 10 A enclosed switching power supply (the perforated metal "LED
//   driver" type, about 200 x 98 x 42 mm). Mains comes in through a panel-mount IEC C14 inlet
//   (the socket a standard C13 "kettle" computer power cable plugs into); 12 V leaves through
//   a cable gland to the fermenter controller.
//
// THIS BOX CONTAINS MAINS VOLTAGE. Read README.md in this folder before printing or wiring it.
//
// HOW TO READ AN OPENSCAD FILE
//   OpenSCAD builds a 3D shape from a description, not by drawing. You combine simple solids:
//     cube(), cylinder()        basic shapes
//     translate([x, y, z])      move the shape that follows
//     rotate([x, y, z])         turn the shape that follows (degrees about each axis)
//     union() { ... }           add shapes together
//     difference() { A; B; C }  start with A and cut B, C, ... out of it
//     hull() { ... }            the tight skin stretched around several shapes
//     module name() { ... }     a reusable recipe, like a function that makes a shape
//   A `%` in front of a shape draws it see-through and leaves it out of the exported part.
//   The numbers at the top are the knobs; everything below is calculated from them.
//
// HOW THE BOX IS LAID OUT (looking down, lid off)
//
//        inlet end      intake fan (blows IN)                    far end
//       +----------[==]-----------------------------------------------+
//  C14  |  wiring  |                                                  |
//  ====>|   bay    |              power supply                        |
// inlet |          |  (its screw terminals face the wiring bay)       |
//       +----||----+-------------------------------------------[==]---+
//            12 V out (cable gland)               exhaust fan (blows OUT)
//
//   Air path: cool air is pulled in low at the wiring-bay end on one side, travels the length
//   of the supply, and is pushed out high at the far end on the opposite side. Mounted on a
//   wall with the inlet end down, that is bottom-in, top-out, the way warm air wants to go.
//
//   Everything is measured from the inside: the cavity is in_l x in_w x in_h, starting at the
//   origin. Walls, the rim flange and the lid are made by growing that cavity shape outward.

part = "assembly";            // "body" | "lid" | "assembly". The export commands above override this.

// --- the power supply. MEASURE YOURS: listings round these numbers.
psu_l = 200;       // length (7.87 in)
psu_w = 98;        // width  (3.85 in)
psu_h = 42;        // height (1.65 in)

// --- the mains inlet: an IEC C14 inlet module with built-in rocker switch and fuse holder,
//     screw-mount type. The defaults are typical for that kind of part, NOT taken from a
//     datasheet. MEASURE YOURS before printing; the cutout must be a close fit.
inlet_cut_w       = 27.5;  // cutout width  (across the box)
inlet_cut_h       = 47.5;  // cutout height (floor to lid direction)
inlet_screw_pitch = 40;    // distance between its two mounting screws, either side of the cutout
inlet_screw_d     = 3.4;   // clearance for M3 screws (use nuts and washers inside)
inlet_flange_h    = 60;    // overall height of the module's front flange
inlet_depth       = 35;    // how far the module and its terminals reach into the box

// --- fit knobs
bay        = 60;   // wiring bay between the inlet wall and the supply's terminals
side_gap   = 3;    // air gap each side of the supply
end_gap    = 2;    // gap at the far end
rail_h     = 4;    // the supply sits on two rails this high, so air can pass underneath
top_air    = 36;   // air space above the supply. The exhaust fan stands in this space; 20 is enough with fans = false
hold_clear = 0.5;  // gap between the lid's hold-down ribs and the top of the supply
dc_gland_d   = 16.3;  // clearance hole for an M16x1.5 cable gland (12 V output cable)
dc_gland_nut = 24;    // across the corners of that gland's nut. MEASURE yours.
dc_gland_z   = 20;    // gland centre above the inside floor
insert_d  = 4.0;   // M3 heat-set insert hole in the rim
groove_w  = 2.6;   // O-ring groove for 2.0 mm cord
groove_d  = 1.5;

// --- mounting ears: flat tabs at the base of the two long walls, for screws
mount_ears = true; // false = a plain box with no ears
ear_w    = 14;     // width of each tab
ear_l    = 18;     // how far a tab sticks out from the wall
ear_t    = 4;      // tab thickness
ear_hole = 4.5;    // hole for an M4 screw

// --- cooling fans: two 25 x 25 x 10 mm 12 V fans, mounted INSIDE against the side walls
//     behind a slotted grill. Typical 25 mm fan dimensions; MEASURE YOURS.
fans        = true;  // false = a sealed box with no grills (then keep the load to about 5 A)
fan_size    = 25;    // the fan's square body
fan_t       = 10;    // the fan's thickness
fan_pitch   = 20;    // distance between the fan's mounting holes
fan_screw_d = 3.0;   // clearance for M2.5 screws through the wall into the fan
grill_slot  = 3;     // width of each grill slot (narrow enough to keep fingers out)
grill_rib   = 1.6;   // plastic left between slots
intake_x    = bay / 2;                       // intake fan: in the wiring bay...
intake_z    = 20;                            // ...low on the wall
exhaust_x   = bay + psu_l - 30;              // exhaust fan: near the far end...
exhaust_z   = rail_h + psu_h + fan_size / 2 + 2;   // ...standing just above the supply

wall = 3; floor_t = 3; lid_t = 4;
flange = 7; flange_h = 8;     // the thicker rim that carries the O-ring groove and the lid screws
r = 4;                        // inside corner radius
$fn = 48;                     // how many flat sides a "round" shape gets

// Derived sizes: the inside of the box and where things sit in it.
in_l = bay + psu_l + end_gap;
in_w = psu_w + 2 * side_gap;
in_h = rail_h + psu_h + top_air;
out_h = floor_t + in_h;
psu_x = bay; psu_y = side_gap;
// The flat part of a wall runs from the outside bottom (-floor_t) up to where the rim flange
// starts (in_h - flange_h). The inlet goes in the middle of that.
flat_top = in_h - flange_h;
inlet_z  = (flat_top - floor_t) / 2;

groove_off = wall + 0.2 + groove_w / 2;      // O-ring groove centreline, measured out from the cavity wall
screw_off  = wall + flange - 3.2;            // lid screw centreline, outside the O-ring

// A box with rounded vertical corners: four cylinders at the corners, wrapped in a hull.
module rrect(l, w, h, rad) {
    hull() for (x = [rad, l - rad], y = [rad, w - rad]) translate([x, y, 0]) cylinder(r = rad, h = h);
}
// The cavity's outline pushed outward by `off` on every side, `h` tall, starting at height z.
// grown(0) is the cavity itself, grown(wall) is the outside of the walls, and so on.
module grown(off, h, z = 0) {
    translate([-off, -off, z]) rrect(in_l + 2 * off, in_w + 2 * off, h, r + off);
}
// The positions of the ten lid screws: four along each long side and one in the middle of each end.
function screw_xy() = let (o = screw_off)
    concat([for (x = [-o, in_l * 0.33, in_l * 0.67, in_l + o], y = [-o, in_w + o]) [x, y]],
           [[-o, in_w / 2], [in_l + o, in_w / 2]]);

// Mounting ears: two tabs on each long wall, flush with the bottom of the box so it sits flat.
// Each hole is 12 mm out from the wall, clear of the rim flange overhanging above.
module ears() {
    if (mount_ears) for (side = [0, 1], x = [12, in_l - 12 - ear_w]) {
        y0 = side == 0 ? -wall - ear_l : in_w + wall - 1;        // the tab overlaps the wall by 1 mm so they fuse
        hole_y = side == 0 ? ear_l - 12 : 1 + 12;
        translate([x, y0, -floor_t]) difference() {
            cube([ear_w, ear_l + 1, ear_t]);
            translate([ear_w / 2, hole_y, -1]) cylinder(d = ear_hole, h = ear_t + 2);
        }
    }
}

// One fan opening, drawn lying flat (looking straight at the wall): a round grill made of
// parallel slots, plus the fan's four screw holes at the corners. The slots are made by
// keeping only the parts of five bars that fall inside a circle (intersection).
module fan_cut() {
    intersection() {
        cylinder(d = fan_size - 2, h = wall + 2);
        for (i = [-2 : 2]) translate([i * (grill_slot + grill_rib) - grill_slot / 2, -fan_size / 2, 0])
            cube([grill_slot, fan_size, wall + 2]);
    }
    for (sx = [-1, 1], sy = [-1, 1]) translate([sx * fan_pitch / 2, sy * fan_pitch / 2, 0])
        cylinder(d = fan_screw_d, h = wall + 2);
}

// The body. Start with the solid outer shape plus the thicker rim flange, then cut away the
// cavity, the O-ring groove, the screw-insert holes, the inlet cutout with its two screw holes,
// the 12 V gland hole and the two fan grills. Then add the parts that hold the supply in place.
module body() {
    difference() {
        union() {
            grown(wall, out_h, -floor_t);
            grown(wall + flange, flange_h, in_h - flange_h);
        }
        grown(0, in_h + 1);                                         // cavity
        translate([0, 0, in_h - groove_d]) difference() {           // O-ring groove
            grown(groove_off + groove_w / 2, groove_d + 1);
            grown(groove_off - groove_w / 2, groove_d + 2, -0.5);
        }
        for (p = screw_xy()) translate([p[0], p[1], in_h - 6.5]) cylinder(d = insert_d, h = 7);
        // Mains inlet: a rectangular hole through the end wall of the wiring bay...
        translate([-wall - 1, in_w / 2 - inlet_cut_w / 2, inlet_z - inlet_cut_h / 2])
            cube([wall + 2, inlet_cut_w, inlet_cut_h]);
        // ...and a screw hole either side of it.
        for (s = [-1, 1]) translate([-wall - 1, in_w / 2 + s * inlet_screw_pitch / 2, inlet_z])
            rotate([0, 90, 0]) cylinder(d = inlet_screw_d, h = wall + 2);
        // 12 V output: a gland hole through the side wall of the wiring bay, well away from the inlet.
        translate([bay / 2, -wall - 1, dc_gland_z]) rotate([-90, 0, 0]) cylinder(d = dc_gland_d, h = wall + 2);
        // Fan grills. rotate([-90, 0, 0]) stands the flat fan_cut() shape up so it passes through
        // a side wall, with its slots running floor-to-lid (which prints cleanly, no supports).
        if (fans) {
            translate([intake_x, in_w - 1, intake_z]) rotate([-90, 0, 0]) fan_cut();     // intake: far side wall, low, in the bay
            translate([exhaust_x, -wall - 1, exhaust_z]) rotate([-90, 0, 0]) fan_cut();  // exhaust: near side wall, high, far end
        }
    }
    // Two rails the supply rests on, leaving an air path underneath it.
    for (f = [0.2, 0.8]) translate([psu_x, psu_y + psu_w * f - 3, 0]) cube([psu_l, 6, rail_h]);
    // Side bumpers: ribs on both long walls that centre the supply, leaving 0.5 mm of play.
    for (x = [psu_x + 20, psu_x + psu_l - 28], y = [0, in_w - (side_gap - 0.5)])
        translate([x, y, 0]) cube([8, side_gap - 0.5, rail_h + 15]);
    // End stop at the far end.
    translate([in_l - (end_gap - 0.5), in_w / 2 - 10, 0]) cube([end_gap - 0.5, 20, rail_h + 15]);
    // Two low stops at the wiring-bay end, at the outer corners so the wires pass between them.
    for (y = [psu_y + 4, psu_y + psu_w - 12]) translate([psu_x - 4, y, 0]) cube([4, 8, rail_h + 12]);
    ears();
}

// The lid: a flat plate the size of the flange with a clearance hole for each screw, plus
// posts underneath that reach down to just above the supply so it cannot lift off its rails.
// Print it upside down (flat face on the bed, posts pointing up).
module lid() {
    difference() {
        grown(wall + flange, lid_t);
        for (p = screw_xy()) translate([p[0], p[1], -1]) cylinder(d = 3.4, h = lid_t + 2);
    }
    rib = top_air - hold_clear;                                   // how far a rib hangs below the lid
    // Four narrow posts, not two wide ribs: wide ribs would wall off the air space above the
    // supply and block the flow from the intake fan to the exhaust fan.
    for (f = [0.25, 0.75], g = [0.25, 0.75])
        translate([psu_x + psu_l * f - 3, psu_y + psu_w * g - 6, -rib]) cube([6, 12, rib]);
}

// Produce the requested part. "assembly" shows the body, a see-through power supply, and the
// lid floating above, for checking the fit by eye.
if (part == "body") body();
else if (part == "lid") lid();
else {
    body();
    %translate([psu_x, psu_y, rail_h]) cube([psu_l, psu_w, psu_h]);
    if (fans) {   // the two fans, shown see-through where they mount inside the walls
        %translate([intake_x - fan_size / 2, in_w - fan_t, intake_z - fan_size / 2]) cube([fan_size, fan_t, fan_size]);
        %translate([exhaust_x - fan_size / 2, 0, exhaust_z - fan_size / 2]) cube([fan_size, fan_t, fan_size]);
    }
    translate([0, 0, in_h + 30]) lid();
}

// Numbers worth knowing, printed in the OpenSCAD console.
echo(oring_length_mm = 2 * (in_l + in_w) - 8 * r + 2 * PI * (r + groove_off));
echo(outside_mm = [in_l + 2 * (wall + flange), in_w + 2 * (wall + flange), out_h + lid_t]);
echo(width_over_ears_mm = in_w + 2 * (wall + (mount_ears ? ear_l : 0)));

// Self-checks: the model refuses to export if a part would not seat properly.
// The inlet's front flange must sit entirely on flat wall, below the rim flange.
assert(inlet_flange_h <= flat_top + floor_t, "the inlet's flange is taller than the flat wall: raise top_air");
assert(inlet_cut_h / 2 <= inlet_z, "the inlet cutout would cut into the floor: raise top_air");
// There must be room behind the inlet for its terminals and for the wires to bend.
assert(bay >= inlet_depth + 20, "the wiring bay is too short for the inlet and its wiring: raise bay");
// Each fan's grill and screw holes must be on flat wall, and the fans must fit inside.
assert(!fans || (exhaust_z + fan_size / 2 <= flat_top && intake_z - fan_size / 2 >= 0),
       "a fan grill runs off the flat wall: raise top_air or move intake_z / exhaust_z");
assert(!fans || exhaust_z - fan_size / 2 >= rail_h + psu_h, "the exhaust fan would hit the supply: raise exhaust_z and top_air");
assert(!fans || intake_x + fan_size / 2 <= bay - 4, "the intake fan does not fit in the wiring bay: raise bay");
// The 12 V gland's nut must sit on flat wall too.
assert(dc_gland_z - dc_gland_nut / 2 >= -floor_t && dc_gland_z + dc_gland_nut / 2 <= flat_top,
       "the 12 V gland nut hits the base or the rim flange: move dc_gland_z");
